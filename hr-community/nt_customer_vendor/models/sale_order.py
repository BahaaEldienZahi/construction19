from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    partner_id = fields.Many2one(
        'res.partner', string='Customer', readonly=False,
        required=True, change_default=True, index=True, tracking=1,
        domain="['&','|',('contact_type','=','customer'),('contact_type','=','both'),'|', ('company_id', '=', False), ('company_id', '=', company_id)]", )
    # parent_id = fields.Many2one('consolidation.group', string='Parent')
    child_ids = fields.One2many(related='partner_id.child_ids')
    partner_invoice_id = fields.Many2one(
        'res.partner', string='Invoice Address',
        readonly=True, required=True,
        domain="['|',('id', '=', partner_id),'&', ('id', 'in', child_ids), ('type', '=', 'invoice')]", )
    partner_shipping_id = fields.Many2one(
        'res.partner', string='Delivery Address', readonly=True, required=True,
        domain="['|',('id', '=', partner_id),'&',('id', 'in', child_ids), ('type', '=', 'delivery')]", )

    @api.depends('partner_id')
    def _compute_partner_shipping_id(self):
        for order in self:
            order.partner_shipping_id = order.partner_id.address_get(['delivery'])[
                'delivery'] if order.partner_id else False

    # commit by create ciustomer no condition
    # @api.onchange('partner_id')
    # def _compute_certain_partner_id(self):
    #     for sale in self:
    #         self.partner_invoice_id = self.partner_id
    #         self.partner_shipping_id = self.partner_id
    #         if sale.partner_id:
    #             current_user = self.env.user.id
    #             partner_user_ids = sale.partner_id.user_ids.ids
    #             partner_team_leaders = [user.user_id.id for user in sale.partner_id.team_ids]
    #             if current_user not in partner_user_ids + partner_team_leaders and not self.user_has_groups(
    #                     'nt_crm_sales_rules.nt_crm_sales_rules_group_coordinator,account.group_account_manager,stock.group_stock_manager'):
    #                 raise UserError(
    #                     _("You are not allowed to submit any transactions with this customer, please contact SC"))
