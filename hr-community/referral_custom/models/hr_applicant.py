from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    salary_proposed_extra = fields.Char("Proposed Salary Extra",
                                        help="Salary Proposed by the Organisation, extra advantages", tracking=True,
                                        groups="base.group_user")
    salary_expected_extra = fields.Char("Expected Salary Extra", help="Salary Expected by Applicant, extra advantages",
                                        tracking=True, groups="base.group_user")

    hide_button = fields.Boolean(compute="compute_hide_button")

    categ_ids = fields.Many2many('hr.applicant.category', readonly=True)

    def _default_referral_by_email(self):
        if self.env.context.get('hide_referal'):
            return self.env.user.email
        else:
            return False

    referral_by_email = fields.Char(readonly=True, default=_default_referral_by_email)

    def compute_hide_button(self):
        for rec in self:
            if rec.user_has_groups('referral_custom.group_referral_hr_Manager'):
                rec.hide_button = False
            else:
                rec.hide_button = True

    @api.model_create_multi
    def create(self, values):
        for vals in values:
            referral_categ = self.env['hr.applicant.category'].search([('name', 'ilike', 'Referral')], limit=1)
            if referral_categ and self.user_has_groups('referral_custom.group_referral_hr_user') and self.env.context.get('hide_referal'):
                vals['categ_ids'] = [(4, referral_categ.id)]
            user = self.env.user
            employee = self.env['hr.employee'].search([('user_id', '=', user.id)])
            if self.env.context.get('hide_referal'):
                vals['ref_employee_id'] = employee.id
                vals['referral_by_email'] = user.login

            res = super(HrApplicant, self).create(vals)
            if res.sudo().attachment_cv_id:
                for attachment in res.sudo().attachment_cv_id:
                    copy_attach = attachment.sudo().copy()
                    copy_attach.sudo().res_model = 'hr.applicant'
                    copy_attach.sudo().res_id = res.id
            return res
