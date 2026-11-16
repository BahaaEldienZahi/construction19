from odoo import models, fields

class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    is_resignation = fields.Boolean(
        string='Resignation Leave'
    )