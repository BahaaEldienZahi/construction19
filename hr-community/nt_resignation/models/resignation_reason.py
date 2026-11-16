from odoo import fields, models

class ResignationReason(models.Model):
    _name = 'resignation.reason'
    _description = 'Resignation Reason'

    name = fields.Char(required=True)