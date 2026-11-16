from odoo import models, fields, _, api
from odoo.exceptions import UserError
from odoo.osv import expression


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    @api.onchange('partner_id')
    def _compute_certain_partner_id(self):
        for lead in self:
            if lead.partner_id:
                current_user = self.env.user.id
                partner_user_ids = lead.partner_id.user_ids.ids
                partner_team_leaders = [user.user_id.id for user in lead.partner_id.team_ids]
                if current_user not in partner_user_ids + partner_team_leaders and not self.user_has_groups(
                        'nt_crm_sales_rules.nt_crm_sales_rules_group_coordinator,account.group_account_manager,stock.group_stock_manager'):
                    raise UserError(
                        _("You are not allowed to submit any transactions with this customer, please contact SC"))
