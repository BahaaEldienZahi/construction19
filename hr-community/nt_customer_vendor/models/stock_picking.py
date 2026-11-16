from odoo import models, fields, _, api
from odoo.exceptions import UserError
from odoo.osv import expression


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.onchange('partner_id')
    def _compute_certain_partner_id(self):
        for stock in self:
            if stock.partner_id:
                current_user = self.env.user.id
                partner_user_ids = stock.partner_id.user_ids.ids
                partner_team_leaders = [user.user_id.id for user in stock.partner_id.team_ids]
                if current_user not in partner_user_ids + partner_team_leaders and not self.user_has_groups(
                        'nt_crm_sales_rules.nt_crm_sales_rules_group_coordinator,account.group_account_manager,stock.group_stock_manager'):
                    raise UserError(
                        _("You are not allowed to submit any transactions with this customer, please contact SC"))
