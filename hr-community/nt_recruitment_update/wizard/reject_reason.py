from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from odoo import Command


class RejectReason(models.Model):
    _name = 'hr.job.reject.reason'
    _description = 'Ht reject reason '

    job_offer = fields.Many2one('hr.job.offer')
    user_id = fields.Many2one('res.users', default=lambda self: self.env.user)
    reason = fields.Text('reject reason ')
    reject_stage = fields.Selection(related='job_offer.state')

    def create(self, val_list):
        if "job_offer" in val_list:
            job_offer_id = self.env['hr.job.offer'].search([('id', '=', val_list['job_offer'])], limit=1)
            if job_offer_id:
                job_offer_id.write({'reject_employee_reason': val_list['reason'], 'reject_type': 'user',
                                    'reject_user': self.env.user.id, 'state': 'reject'})

        return super(RejectReason, self).create(val_list)
