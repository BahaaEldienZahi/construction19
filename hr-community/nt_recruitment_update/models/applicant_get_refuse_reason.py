from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class ApplicantGetRefuseReason(models.TransientModel):
    _inherit = 'applicant.get.refuse.reason'

    applicant_id = fields.Many2one(
        'hr.applicant'
    )

    # def action_refuse_reason_apply(self):
    #     res = super(ApplicantGetRefuseReason, self).action_refuse_reason_apply()
    #     template = self.env.ref(
    #         'nt_recruitment_update.email_template_rejection_mail')
    #     template.send_mail(self.applicant_id.id, force_send=True)
    #     return res
