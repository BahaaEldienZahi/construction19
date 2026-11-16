from odoo import fields, models


class PolicyCustomLine(models.Model):
    _name = 'policy.custom.line'
    _description = 'Policy Line'

    category_id = fields.Many2one(
        'employee.category',
        string='Category'
    )
    subcategory_id = fields.Many2one(
        'employee.subcategory',
        string='Sub Category',
        domain="[('category_id', '=', category_id)]"
    )
    first = fields.Float('First Time', default=1)
    second = fields.Float('Second Time', default=1)
    third = fields.Float('Third Time', default=1)
    fourth = fields.Float('Fourth Time', default=1)
    fifth = fields.Float('Fifth Time', default=1)