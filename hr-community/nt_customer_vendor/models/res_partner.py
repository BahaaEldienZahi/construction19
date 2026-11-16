from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def default_get(self, fields_list):
        defaults = super(ResPartner, self).default_get(fields_list)
        res_partner_search_mode = self.env.context.get('res_partner_search_mode')
        if res_partner_search_mode == 'customer':
            defaults['contact_type'] = 'customer'
        if res_partner_search_mode == 'supplier':
            defaults['contact_type'] = 'vendor'

            # defaults['vendor_type'] = 'internal'

        return defaults

    contact_type = fields.Selection(
        [
            ('customer', 'Customer'),
            ('vendor', 'Vendor'),
            ('both', 'Both'),
            ('contact', 'Contact'),
        ],
        string='Partner Type')
    # vendor_type = fields.Selection(
    #     [
    #         ('internal', 'Internal'),
    #         ('external', 'External'),
    #     ],
    #     string='Vendor Type')
    team_ids = fields.Many2many('crm.team', string='Sales Team')
    use_excel = fields.Boolean('Using Excel')
    foreign_name = fields.Char(string='Foreign Name')

    # @api.onchange('contact_type')
    # def compute_vendor_type(self):
    #     for rec in self:
    #         if rec.contact_type != "vendor":
    #             rec.vendor_type = False


