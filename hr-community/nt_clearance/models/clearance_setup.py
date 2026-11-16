from odoo import models, fields, api


class ClearanceSetup(models.Model):
    _name = 'clearance.setup'
    _description = 'Clearance Setup'
    _order = 'sequence, id'

    name = fields.Char(string="Item", required=True)

    department_id = fields.Many2one(
        'hr.department',
        string="Department",
        required=True,
        index=True
    )

    sequence = fields.Integer(string="Sequence",required=True)

    owner_ids = fields.Many2many(
        'res.users',
        'clearance_setup_res_users_rel',
        'setup_id',
        'user_id',
        string="Owners",
        required=True,
    )

