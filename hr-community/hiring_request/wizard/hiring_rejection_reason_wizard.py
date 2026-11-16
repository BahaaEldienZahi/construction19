from odoo import fields, models


class HiringRejectionReasonWizard(models.TransientModel):
    _name = 'hiring.rejection.reason.wizard'
    _description = 'Hiring Rejection Reason Wizard'

    reject_reason = fields.Text()

    def button_confirm(self):
        request = self.env['hiring.request'].browse(self._context.get('active_id'))
        request.status = 'reject'
        request.rejection_reason = self.reject_reason

