from odoo import models, fields, api


class ProductProduct(models.Model):
    _inherit = 'product.product'

    helpdesk_category_id = fields.Many2one('helpdesk.category', string='Helpdesk Category', store=True)

    @api.onchange('helpdesk_category_id')
    def update_helpdesk_category(self):
        for rec in self:
            rec.product_tmpl_id.helpdesk_category_id = rec.helpdesk_category_id


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    helpdesk_category_id = fields.Many2one('helpdesk.category', string='Helpdesk Category', store=True)

    @api.onchange('helpdesk_category_id')
    def update_helpdesk_category(self):
        for rec in self:
            rec.product_variant_id.helpdesk_category_id = rec.helpdesk_category_id
