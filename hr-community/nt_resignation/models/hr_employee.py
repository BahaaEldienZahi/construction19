from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    is_resigned = fields.Boolean('Is Resigned?', default=False)

    @api.model
    def _get_employee_vals(self):
        self.ensure_one()
        return self.id, self.date_start