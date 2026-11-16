from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    archive_end_date = fields.Integer(config_parameter='nt_employee_contract.archive_end_date')
    day_of_previous_month = fields.Integer(config_parameter='nt_employee_contract.day_of_previous_month')
