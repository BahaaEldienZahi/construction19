import html
from odoo import models, fields, api, _
from datetime import date
from dateutil.relativedelta import relativedelta


class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    fellowship_fund = fields.Boolean(string="Fellowship Fund")


    def toggle_active(self):
        if self.env.context.get('toggle_active', False) and self.active:
            active_employee_contact = self.env['res.partner'].search([('employee_ids', 'in', self.ids),('active', '=', True),])
            active_employee_contact.action_archive()
        else:
            unactive_employee_contact = self.env['res.partner'].search([('employee_ids', 'in', self.ids),('active', '=', False),])
            unactive_employee_contact.action_unarchive()
        return super(HrEmployee, self).toggle_active()

    @api.model_create_multi
    def create(self, vals_list):
        for val in vals_list:
            if not val.get('probation_period_end_date'):
                val['probation_period_end_date'] = date.today() + relativedelta(months=3)

        res = super(HrEmployee, self).create(vals_list)
        if res:
            for rec in res:

                att_policy_id = self.env['ir.config_parameter'].sudo().get_param(
                        'rm_hr_attendance_sheet.attendance_policy_id')
                if att_policy_id:
                    contract_id = self.env['hr.contract'].create({
                        'name': f"{res.name} Contract",
                        'state': 'open',
                        'employee_id': rec.id,
                        'wage': 0,
                        'date_start': rec.date_start,
                        'probation_date_end': rec.probation_period_end_date,
                        'date_end': rec.contract_end_date,
                        'att_policy_id': int(att_policy_id),
                    })
                    rec.contract_id = contract_id.id
                else:
                    contract_id = self.env['hr.contract'].create({
                        'name': f"{res.name} Contract",
                        'state': 'open',
                        'employee_id': rec.id,
                        'wage': 0,
                        'date_start': rec.date_start if rec.date_start else fields.Date.today(),
                        'probation_date_end': rec.probation_period_end_date,
                        'date_end': rec.contract_end_date,
                    })
                    rec.contract_id = contract_id.id

                # on_board.send_mail()

            # probation_period = self.env['employee.probation.period'].create({'employee_id': res.id,
            #                                                                  'department_id': val['department_id']})

        return res

    def probation_period_end_date_notification(self):
        employees = self.env['hr.employee'].search([])
        for employee in employees:
            if str(date.today()) == str(employee.probation_period_end_date):

                probation_period = self.env['employee.probation.period'].search([('employee_id', '=', employee.id)])

                base_url_employee = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                record_url_employee = "{}/web#id={}&model={}".format(base_url_employee, probation_period.id, 'employee.probation.period')
                link = "{}".format(record_url_employee, html.escape(probation_period.employee_id.name))

                body = _(f"Probation period for employee: {employee.name}, ID: {employee.id} has ended, link: {link}")
                manager = employee.parent_id.user_id
                if manager:
                    manager_partner = manager.partner_id

                    channel = self.env['discuss.channel'].channel_get([manager_partner.id])
                    channel_id = self.env['discuss.channel'].browse(channel["id"])
                    channel_id.message_post(
                        subject="Probation period ended",
                        body=body,
                        message_type='comment',
                        subtype_xmlid='mail.mt_comment',
                    )

    # @api.depends('date_start')
    # def _compute_probation_period_end_date(self):
    #     for rec in self:
    #         if rec.date_start:
    #             rec.probation_period_end_date = rec.date_start + relativedelta(months=3)
    #             rec.date_end = rec.probation_period_end_date
    #         else:
    #             rec.probation_period_end_date = False
    #             rec.date_end = False
