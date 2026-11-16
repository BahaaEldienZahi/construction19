from odoo import models, fields, api

class ClearanceSetupItem(models.Model):
    _name = 'clearance.setup.item'
    _description = 'Clearance Setup Item'
    _order = 'sequence, id'

    setup_id = fields.Many2one('clearance.setup', required=True, ondelete='cascade', index=True)
    name = fields.Char(string="Item", required=True)
    department_id = fields.Many2one('hr.department',related='setup_id.department_id')
    sequence = fields.Integer(string="Sequence", default=10)

    def write(self, vals):
        res = super().write(vals)
        # If item name changes, update related lines
        if 'name' in vals:
            lines = self.env['clearance.request.line'].search([('item_id', 'in', self.ids)])
            for line in lines:
                line.name = line.item_id.name
        return res