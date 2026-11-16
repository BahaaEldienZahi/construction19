from odoo import api, fields, models


class HrContract(models.Model):

    _inherit = 'hr.contract'

    leave_value = fields.Float()

