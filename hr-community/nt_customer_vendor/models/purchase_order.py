# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import models, fields, api,_
from odoo.exceptions import UserError



class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def default_vendor(self):
        if not self.env.user.has_group('purchase.group_purchase_manager'):
            other = self.env['res.partner'].search([('is_other','=',True)],limit=1)
            return  other
        else:
            return
    partner_id = fields.Many2one('res.partner', string='Vendor', required=True,
                                 default=default_vendor,
                                 change_default=True, tracking=True,
                                 domain="['&','|',('contact_type','=','vendor'),('contact_type','=','both'),'|', ('company_id', '=', False), ('company_id', '=', company_id)]",
                                 help="You can find a vendor by its Name, TIN, Email or Internal Reference.")
    dest_address_id = fields.Many2one('res.partner',
                                      domain="['&','|',('contact_type','=','vendor'),('contact_type','=','both'),'|', ('company_id', '=', False), ('company_id', '=', company_id)]",
                                      string='Dropship Address',
                                      help="Put an address if you want to deliver directly from the vendor to the customer. "
                                           "Otherwise, keep empty to deliver to your own company.")
    vendor_readonly = fields.Boolean(string='Vendor Edit', compute='_compute_vendor_edit')



    @api.onchange('partner_id')
    def _compute_vendor_edit(self):
        for rec in self:
            current_user = self.env.user
            if current_user.has_group('purchase.group_purchase_manager') :
                rec.vendor_readonly =False
            elif current_user.has_group('purchase.group_purchase_user'):
                rec.vendor_readonly = rec.vendor_readonly =True
            else:
                rec.vendor_readonly = True

    @api.model
    def default_get(self, fields):
        defaults = super(PurchaseOrder, self).default_get(fields)
        default_vendor = self.env['res.partner'].search([('name', '=', 'other')])
        if default_vendor :
            defaults['partner_id'] = default_vendor.id
        else:
            # not default vendor assign first vendor
            pass

        return defaults