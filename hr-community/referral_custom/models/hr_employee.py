from odoo import models, fields, api
from datetime import date


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    ref_employee_id = fields.Many2one(
        'hr.employee', string='Referral By Employee'
    )
    referral_by_email = fields.Char()
    categ_ids = fields.Many2many('hr.applicant.category', string="Tag")
    payment_id = fields.Many2one(
        'account.payment'
    )

    # @api.onchange('ref_employee_id')
    # def onchange_categ_ids(self):
    #     referral_categ = self.env['hr.applicant.category'].search([('name','like', 'Referral')], limit=1)
    #     if self.ref_employee_id:
    #         self.categ_ids = [(4, referral_categ.id)]
    #         partner = self.env['res.partner'].search(
    #             [('email', '=', self.referral_by_email)], limit=1)
    #         if partner:
    #             self.referred_partner_id = partner.id

    def _create_payment(self):
        for rec in self:
            Config = self.env['ir.config_parameter'].sudo()
            amount = float(Config.get_param('referral_custom.amount'))
            memo = Config.get_param('referral_custom.memo')
            code = self.env['account.journal'].sudo().search([('type', '=', 'bank')], limit=1)
            if not rec.in_probation_period and rec.ref_employee_id:
                rec.payment_id = self.env['account.payment'].sudo().create(
                    {
                        # 'name': code.code,
                        'amount': amount,
                        'ref': memo,
                        'date': date.today(),
                        'payment_type': 'outbound',
                        'partner_type': 'supplier',
                        'partner_id': rec.ref_employee_id.user_id.partner_id.id,
                    })
                rec.payment_id.sudo().action_post()