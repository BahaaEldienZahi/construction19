# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    def get_partner_domain(self):
        context = self._context
        if context.get('default_move_type'):
            if context.get('default_move_type') in ['out_invoice', 'out_refund', 'out_receipt']:
                return ['&', '|', ('contact_type', '=', 'customer'), ('contact_type', '=', 'both'), '|',
                        ('company_id', '=', False), ('company_id', '=', self.env.company.id)]
            if context.get('default_move_type') in ['in_invoice', 'in_refund', 'in_receipt']:
                return ['&', '|', ('contact_type', '=', 'vendor'), ('contact_type', '=', 'both'), '|',
                        ('company_id', '=', False), ('company_id', '=', self.env.company.id)]
            else:
                return ['|',
                        ('company_id', '=', False), ('company_id', '=', self.env.company.id)]

    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        readonly=True,
        tracking=True,
        # inverse='_inverse_partner_id',
        domain=get_partner_domain,
        check_company=True,
        change_default=True,
        ondelete='restrict',
    )
    child_ids = fields.One2many(related='partner_id.child_ids')

    partner_shipping_id = fields.Many2one(
        'res.partner', string='Delivery Address', readonly=True, required=False,)

    # @api.onchange('partner_id')
    # def _inverse_partner_id(self):
    #     for invoice in self:
    #         if invoice.partner_id and invoice.move_type == 'out_invoice':
    #             current_user = self.env.user.id
    #             partner_user_ids = invoice.partner_id.user_ids.ids
    #             partner_team_leaders = [user.user_id.id for user in invoice.partner_id.team_ids]
    #             if current_user not in partner_user_ids + partner_team_leaders and not self.user_has_groups(
    #                     'nt_crm_sales_rules.nt_crm_sales_rules_group_coordinator,account.group_account_manager,stock.group_stock_manager'):
    #                 raise UserError(
    #                     _("You are not allowed to submit any transactions with this customer, please contact SC"))
    #         if invoice.is_invoice(True):
    #             for line in invoice.line_ids + invoice.invoice_line_ids:
    #                 if line.partner_id != invoice.commercial_partner_id:
    #                     line.partner_id = invoice.commercial_partner_id
    #                     line._inverse_partner_id()
