from datetime import datetime, timedelta

from odoo import api, fields, models, tools, SUPERUSER_ID, _
from odoo.exceptions import ValidationError,UserError


class Boarding(models.Model):
    _name = 'boarding.boarding'
    _description = 'boarding boarding'
    _rec = 'name'
    _inherit = ['mail.thread.cc', 'mail.activity.mixin']

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        search_domain = []
        stage_ids = stages._search(search_domain, order=order, access_rights_uid=SUPERUSER_ID)
        return stages.browse(stage_ids)

    def _get_default_stage_id(self):
        return self.env['boarding.stage'].search([], order='sequence', limit=1)

    stage_id = fields.Many2one('boarding.stage', string='Stage', index=True, tracking=True,
                               domain="[]",
                               copy=False,
                               group_expand='_read_group_stage_ids',
                               default=_get_default_stage_id)
    employee_id = fields.Many2one('hr.employee')
    name = fields.Char(string='Name', related='employee_id.name')
    department_id = fields.Many2one('hr.department', string='Department', related='employee_id.department_id')
    partner_mobile = fields.Char(string="Mobile", required=False, )
    work_email = fields.Char(string="Work Email", required=False, )
    responsible_id = fields.Many2one('hr.employee', string='Responsible', related='stage_id.responsible_id')
    new_responsible_id = fields.Many2one('hr.employee', string='new Responsible',)

    is_done = fields.Boolean(string="Done", default=False)





    def send_mail(self):
        for rec in self:
            rec.new_responsible_id = rec.stage_id.responsible_id.id
            rec.message_post_with_source('nt_recruitment_update.email_template_new_employee_reminder', **{
                'subtype_id': rec.env['ir.model.data']._xmlid_to_res_id('mail.mt_note'),
                'email_layout_xmlid': 'mail.mail_notification_light',
            })

    def send_activity(self):
        for rec in self:
            user_id = rec.stage_id.responsible_id.user_id
            date_deadline = datetime.now() + timedelta(days=2)
            activity_type_id = rec.env['mail.activity.type'].search([('id', '=', 4)]).id
            data = {
                'res_id': rec._origin.id,
                'res_model_id': rec.env['ir.model'].search([('model', '=', 'boarding.boarding')]).id,
                'user_id': user_id.id,
                'summary': 'New employee Reminder',
                'activity_type_id': activity_type_id,
                'date_deadline': date_deadline
            }
            a= rec.env['mail.activity'].create(data)

    def action_move(self):
        for rec in self:
            if rec.is_done:
                self.send_activity()
                self.send_mail()
                rec.is_done = False
                new_stage = self.env['boarding.stage'].search([
                    ('sequence', '>', rec.stage_id.sequence),
                ], order='sequence ASC',limit=1)
                if new_stage.id:
                    rec.sudo().write({
                        'stage_id':new_stage.sudo().id
                    })
                else:
                    rec.sudo().write({
                        'stage_id': rec.stage_id.sudo().id
                    })
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'boarding.boarding',
                    'view_mode': 'kanban,list,form',
                    'name': 'On boarding Kanban'
                }
            else:
                if rec.ids:
                    raise ValidationError(_("Please Mark as Done"))

    @api.onchange('stage_id')
    def check_stage(self):
        for rec in self:
            if rec.is_done:
                rec.is_done = False
                rec.sudo().write({
                    'is_done': False
                })
                self.send_activity()
                self.send_mail()
            else:
                if self.ids:
                    raise ValidationError(_("Please Mark Done to be done"))

