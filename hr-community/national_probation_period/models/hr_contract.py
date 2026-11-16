# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import MissingError, UserError, ValidationError, AccessError
from datetime import datetime
from dateutil.relativedelta import relativedelta
from datetime import date


class HrContract(models.Model):
    _inherit = "hr.contract"

    probation_date_end = fields.Date('Probation End Date', tracking=True,
                                     help="End date of the contract (if it's a fixed-term contract).")
    is_auto_allocate_timeoff = fields.Boolean(default=False, copy=False)

    # @api.depends('date_start')
    # def _compute_probation_date_end(self):
    #     for rec in self:
    #         if rec.date_start:
    #             rec.probation_date_end = rec.date_start + relativedelta(months=3)
    #         else:
    #             rec.probation_date_end = False

    # @api.onchange('date_end')
    # def onchange_date_end(self):
    #     self.probation_date_end = self.date_end

    # def write(self, vals):
    #     res = super(HrContract, self).write(vals)
    #     # re = self.env['hr.leave.allocation'].search([])
    #     # for i in re:
    #     #     i.write({'state': 'draft'})
    #
    #     hr_timeoff_type_objs = self.env['hr.leave.type'].search([('auto_allocation', '=', True)])
    #     li = []
    #     for i in hr_timeoff_type_objs:
    #         li.append(i.id)
    #
    #     time_allocation_objs = self.env['hr.leave.allocation'].search(
    #         [('holiday_status_id', 'in', li),
    #          ('employee_id', '=', self.employee_id.id)])
    #     if time_allocation_objs and not self.is_auto_allocate_timeoff:
    #         return res
    #     else:
    #         # 4 if not create
    #         if self.employee_id.in_probation_period:
    #             if not self.is_auto_allocate_timeoff:
    #                 return res
    #             else:
    #                 for obj in hr_timeoff_type_objs:
    #                     allocation_object = {
    #                         'name': obj.name + str(self.employee_id.name) + "NEW AT",
    #                         'employee_id': self.employee_id.id,
    #                         'holiday_status_id': obj.id,
    #                         'number_of_days': int(
    #                             (obj.defr_days / 12) * (13 - self.date_start.month)),
    #                     }
    #                     time_allocation = self.env['hr.leave.allocation'].sudo().create(allocation_object)
    #                     time_allocation.action_validate()
    #                     self.is_auto_allocate_timeoff = False
    #                 return res
    #         else:
    #             for obj in hr_timeoff_type_objs:
    #                 allocation_object = {
    #                     'name': obj.name + str(self.employee_id.name),
    #                     'employee_id': self.employee_id.id,
    #                     'holiday_status_id': obj.id,
    #                     'number_of_days': int(
    #                         (obj.auto_allocation_days / 12) * (13 - self.date_start.month)),
    #                 }
    #                 time_allocation = self.env['hr.leave.allocation'].sudo().create(allocation_object)
    #                 time_allocation.action_validate()
    #             return res
    #     return res

    def write(self, vals):
        res = super(HrContract, self).write(vals)
        if 'last_generation_date' in vals:
            return res
        # re = self.env['hr.leave.allocation'].search([])
        # for i in re:
        #     i.write({'state': 'draft'})
        for rec in self:

            hr_timeoff_type_objs = self.env['hr.leave.type'].search([('auto_allocation', '=', True)])
            li = []
            for i in hr_timeoff_type_objs:
                li.append(i.id)

            for emp in rec.employee_id:
                time_allocation_objs = self.env['hr.leave.allocation'].search(
                    [('holiday_status_id', 'in', li),
                     ('employee_id', '=', emp.id)])
                if time_allocation_objs and not emp.contract_id.is_auto_allocate_timeoff:
                    return res
                else:
                    # 4 if not create
                    if emp.in_probation_period:
                        if not emp.contract_id.is_auto_allocate_timeoff:
                            return res
                        else:
                            for obj in hr_timeoff_type_objs:
                                month = fields.Date.to_date(rec.date_start).month

                                no_days = (obj.auto_allocation_days / 12) * (13 - month)
                                if obj.probation_period:
                                    no_days = abs(no_days - obj.probation_period_days)

                                float_no = no_days - int(no_days)
                                if float_no == 0.75 or float_no == 0.25:
                                    no_days -= 0.25
                                else:
                                    no_days = int(no_days)
                                allocation_object = {
                                    'name': obj.name + str(emp.name) + " NEW AT",
                                    'employee_id': emp.id,
                                    'holiday_status_id': obj.id,
                                    'number_of_days': int(no_days) if obj.probation_period else no_days
                                }
                                if no_days > 0:
                                    time_allocation = self.env['hr.leave.allocation'].sudo().create(allocation_object)
                                    time_allocation.action_validate()
                            emp.contract_id.is_auto_allocate_timeoff = False
                            return res
                    else:
                        month = fields.Date.to_date(rec.date_start).month
                        for obj in hr_timeoff_type_objs:

                            allocation_object = {
                                'name': obj.name + str(emp.name),
                                'employee_id': emp.id,
                                'holiday_status_id': obj.id,
                                'number_of_days': int(1.75 * (13 - month)),
                            }
                            # (obj.auto_allocation_days / 12)/ == 1.75
                            time_allocation = self.env['hr.leave.allocation'].sudo().create(allocation_object)
                            time_allocation.action_validate()
                        return res
        return res

    @api.constrains('date_end')
    def _probation_period_validate(self):
        for rec in self:
            if not rec.employee_id.remain_probation_period <= 180:
                raise ValidationError("You Can't Extending More Than 6 Month From Probation Period")

    def _cancel_contracts(self):
        contracts = self.search([('state', '=', 'open'), ('date_start', '<=', fields.Date.today())])
        for contract in contracts:
            if contract.date_end:
                if contract.date_end <= fields.Date.today():
                    contract.state = 'cancel'

    @api.model
    def update_state(self):
        from_cron = 'from_cron' in self.env.context
        companies = self.env['res.company'].search([])
        contracts = self.env['hr.contract']
        work_permit_contracts = self.env['hr.contract']
        for company in companies:
            contracts += self.search([
                ('state', '=', 'open'), ('kanban_state', '!=', 'blocked'), ('company_id', '=', company.id),
                '&',
                ('date_end', '<=', fields.Date.today() + relativedelta(days=company.contract_expiration_notice_period)),
                ('date_end', '>=', fields.Date.today() + relativedelta(days=1)),
            ])

            work_permit_contracts += self.search([
                ('state', '=', 'open'), ('kanban_state', '!=', 'blocked'), ('company_id', '=', company.id),
                '&',
                ('employee_id.work_permit_expiration_date', '<=',
                 fields.Date.today() + relativedelta(days=company.work_permit_expiration_notice_period)),
                ('employee_id.work_permit_expiration_date', '>=', fields.Date.today() + relativedelta(days=1)),
            ])

        for contract in contracts:
            contract.with_context(mail_activity_quick_update=True).activity_schedule(
                'mail.mail_activity_data_todo', contract.date_end,
                _("The contract of %s is about to expire.", contract.employee_id.name),
                user_id=contract.hr_responsible_id.id or self.env.uid)
            contract.message_post(
                body=_(
                    "According to the contract's end date, this contract has been put in red on the %s. Please advise and correct.",
                    fields.Date.today()
                )
            )

        for contract in work_permit_contracts:
            contract.with_context(mail_activity_quick_update=True).activity_schedule(
                'mail.mail_activity_data_todo', contract.date_end,
                _("The work permit of %s is about to expire.", contract.employee_id.name),
                user_id=contract.hr_responsible_id.id or self.env.uid)
            contract.message_post(
                body=_(
                    "According to Employee's Working Permit Expiration Date, this contract has been put in red on the %s. Please advise and correct.",
                    fields.Date.today()
                )
            )

        if contracts:
            contracts._safe_write_for_cron({'kanban_state': 'blocked'}, from_cron)
        if work_permit_contracts:
            work_permit_contracts._safe_write_for_cron({'kanban_state': 'blocked'}, from_cron)

        contracts_to_close = self.search([
            ('state', '=', 'open'),
            '|',
            ('date_end', '<=', fields.Date.to_string(date.today())),
            ('employee_id.work_permit_expiration_date', '<=', fields.Date.to_string(date.today())),
        ])

        if contracts_to_close:
            contracts_to_close._safe_write_for_cron({'state': 'cancel'}, from_cron)

        contracts_to_open = self.search([('state', '=', 'draft'), ('kanban_state', '=', 'done'),
                                         ('date_start', '<=', fields.Date.to_string(date.today())), ])

        if contracts_to_open:
            contracts_to_open._safe_write_for_cron({'state': 'open'}, from_cron)

        contract_ids = self.search([('date_end', '=', False), ('state', '=', 'cancel'), ('employee_id', '!=', False)])
        # Ensure all closed contract followed by a new contract have a end date.
        # If closed contract has no closed date, the work entries will be generated for an unlimited period.
        for contract in contract_ids:
            next_contract = self.search([
                ('employee_id', '=', contract.employee_id.id),
                ('state', 'not in', ['cancel', 'draft']),
                ('date_start', '>', contract.date_start)
            ], order="date_start asc", limit=1)
            if next_contract:
                contract._safe_write_for_cron({'date_end': next_contract.date_start - relativedelta(days=1)}, from_cron)
                continue
            next_contract = self.search([
                ('employee_id', '=', contract.employee_id.id),
                ('date_start', '>', contract.date_start)
            ], order="date_start asc", limit=1)
            if next_contract:
                contract._safe_write_for_cron({'date_end': next_contract.date_start - relativedelta(days=1)}, from_cron)

        return True
