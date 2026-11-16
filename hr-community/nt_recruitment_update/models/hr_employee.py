from datetime import timedelta,datetime
from odoo import models, fields, api


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    activity_reminder_sent = fields.Boolean(string='Activity Reminder Sent', default=False)
    referred_partner_id = fields.Many2one('res.partner', string='Customer', )
    is_confirmed = fields.Boolean(string="Confirm Joining date", default=False)
    send_to = fields.Many2one('res.users')

    @api.model
    def _cron_send_activity_reminder(self):
        today = fields.Date.today()
        contracts = self.search([('probation_period_end_date', '>=', today), ('activity_reminder_sent', '=', False)])
        for contract in contracts:
            days_until_end = (contract.probation_period_end_date - today).days
            if days_until_end <= 5:
                contract.send_activity_reminder(contract)

    def send_activity_reminder(self, contract):
        if contract.parent_id.user_id:
            activity_type_id = self.env['mail.activity.type'].search([('id', '=', 4)]).id
            for rec in self:
                activity_summary = 'Contract End Reminder'
                activity_date_deadline = rec.probation_period_end_date - timedelta(days=5)
                self.env['mail.activity'].create([{
                    'activity_type_id': activity_type_id,
                    'res_id': self.id,
                    'res_model_id': self.env['ir.model'].search(
                        [('model', '=', 'hr.employee')]).id,
                    'date_deadline': activity_date_deadline,
                    'summary': activity_summary,
                    'user_id': contract.parent_id.user_id.id
                }])
                self.activity_reminder_sent = True

    def send_mail(self,user):
        for rec in self:
            self.send_to = user.id
            rec.message_post_with_source('nt_recruitment_update.email_template_new_employee_check', **{
                'subtype_id': rec.env['ir.model.data']._xmlid_to_res_id('mail.mt_note'),
                'email_layout_xmlid': 'mail.mail_notification_light',
            })

    def send_activity(self,user):
        for rec in self:
            date_deadline = datetime.now()
            activity_type_id = rec.env['mail.activity.type'].search([('id', '=', 4)]).id
            data = {
                'res_id': self.id,
                'res_model_id': rec.env['ir.model'].search([('model', '=', 'hr.employee')]).id,
                'user_id': user.id,
                'summary': 'please check new Employee',
                'activity_type_id': activity_type_id,
                'date_deadline':date_deadline,
            }
            a= rec.env['mail.activity'].create(data)

    @api.model
    def _cron_send_check_employee(self):
        today = fields.Date.today()
        new_employees = self.search([('date_start', '=', today)])
        users = self.env['res.users'].search([])
        for employee in new_employees:
            for user in users:
                if user.has_group('hr.group_hr_manager'):
                    employee.send_activity(user)
                    employee.send_mail(user)

                else:
                    continue
