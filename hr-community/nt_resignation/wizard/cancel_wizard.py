from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime
from dateutil.relativedelta import relativedelta


class ResignationCancel(models.Model):
    _name = 'hr.resignation.cancel'
    resignation_id = fields.Many2one('hr.resignation')

    cancel_reason = fields.Selection([('rejoin', 'Same salary'), ('counter_offer', 'Adjust salary')])
    old_salary = fields.Float(string='Old Salary', compute="compute_old_salary", store=1)
    new_salary = fields.Float(string='New Salary', default=0)
    date_from = fields.Date(string='Start Date')

    # request_salary = fields.Float('requested salary')
    # new_date_request = fields.Date('new request Date')

    @api.depends('cancel_reason')
    def compute_old_salary(self):
        for rec in self:
            if rec.cancel_reason == 'counter_offer':
                if rec.resignation_id.employee_id and rec.resignation_id.employee_id.contract_id.wage > 0.0:
                    rec.old_salary = rec.resignation_id.employee_id.contract_id.wage
                else:
                    rec.old_salary = 0.0
            else:
                pass

    def action_confirm(self):
        self.ensure_one()
        if self.cancel_reason == 'rejoin':
            self.rejoin_action()

        elif self.cancel_reason == 'counter_offer':
            self._action_counter_offer()
            self.resignation_id.state = 'counter_offer'
        elif self.cancel_reason == 'change_date':
            pass

    def rejoin_action(self):
        self.ensure_one()
        emp = self.resignation_id.employee_id
        contract_id = emp.sudo().contract_id
        if not contract_id:
            raise ValidationError('selected employee dosent has active contract ')

        else:
            contract_id.write({
                'date_end': None
            })
            emp.write({
                'is_resigned': False,
                'contract_end_date': None})
            self.resignation_id.state = 'rejoin'

    def _action_counter_offer(self):
        if self.cancel_reason == 'counter_offer':
            current_contract = self.resignation_id.employee_id.contract_id
            # current_contract.is_auto_allocate_timeoff = True
            current_contract.probation_date_end = False
            current_contract.date_end = self.date_from + relativedelta(days=-1)
            self.resignation_id.employee_id.sudo()._create_payment()
            # current_contract.write({'state': 'cancel'})
            wage = current_contract.wage + self.new_salary
            contract_id = self.env['hr.contract'].sudo().create({
                'name': f"{current_contract.name} ",
                'state': 'open',
                'employee_id': self.resignation_id.employee_id.id,
                'wage': self.new_salary,
                'date_start': self.date_from,
                'att_policy_id': current_contract.att_policy_id.id
            })
            current_contract_end_date = self.date_from.strftime('%Y-%m-%d')
            new_contract_str_date = contract_id.date_start.strftime('%Y-%m-%d')
            contract_id.date_end = False
            self.resignation_id.employee_id.contract_id = contract_id.id
            current_date = str(datetime.now().date())
            if new_contract_str_date == current_date and current_contract_end_date == current_date:
                current_contract.write({'state': 'cancel'})
                contract_id.state = 'open'
            self.resignation_id.employee_id.is_resigned = False
            # self.resignation_id.employee_id.contract_end_date = None
            # previous_date_from = self.date_from + relativedelta(days=-1)
            # current_contract.write({'date_end': previous_date_from})
        else:
            pass

    # def _action_change_date(self):
    #     self.ensure_one()
    #
    #     if not self.new_date_request:
    #         raise ValidationError(' New Date request must be submit')
    #     else:
    #         new_request = self.env['hr.resignation'].create({
    #             'employee_id': self.resignation_id.employee_id.id,
    #             'resignation_date': self.new_date_request,
    #
    #         }
    #         )
    #         if new_request:
    #             self.resignation_id.related_request = new_request
