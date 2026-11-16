from odoo import models, fields, api,_
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def get_partner_domain(self):
        context = self._context
        if context.get('default_payment_type') and context.get('default_partner_type') :
            if context.get('default_payment_type') == 'inbound' and context.get('default_partner_type') ==  'customer':
                return ['&', '|', ('contact_type', '=', 'customer'), ('contact_type', '=', 'both'), '|',
                        ('company_id', '=', False), ('company_id', '=', self.env.company.id)]
            if context.get('default_payment_type') == 'outbound' and context.get('default_partner_type') ==  'supplier':
                return ['&', '|', ('contact_type', '=', 'vendor'), ('contact_type', '=', 'both'), '|',
                        ('company_id', '=', False), ('company_id', '=', self.env.company.id)]
            else:
                return ['|',
                        ('company_id', '=', False), ('company_id', '=', self.env.company.id)]

    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string="Customer/Vendor",
        store=True, readonly=False, ondelete='restrict',
        compute='_compute_partner_id',
        domain=get_partner_domain,
        tracking=True,
        check_company=True)

    @api.depends('is_internal_transfer')
    def _compute_partner_id(self):
        for pay in self:
            if pay.is_internal_transfer:
                pay.partner_id = pay.journal_id.company_id.partner_id
            elif pay.partner_id == pay.journal_id.company_id.partner_id:
                pay.partner_id = False
            else:
                pay.partner_id = pay.partner_id

    # @api.onchange('partner_id')
    # def _compute_certain_partner_id(self):
    #     for payment in self:
    #         if payment.partner_id:
    #             current_user = self.env.user.id
    #             partner_user_ids = payment.partner_id.user_ids.ids
    #             partner_team_leaders = [user.user_id.id for user in payment.partner_id.team_ids]
    #             if current_user not in partner_user_ids + partner_team_leaders:
    #                 raise UserError(_("You are not allowed to submit any transactions with this customer, please contact SC"))

