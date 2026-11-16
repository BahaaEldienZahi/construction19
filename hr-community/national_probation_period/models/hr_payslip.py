from odoo import fields, models, api


class payslip(models.Model):
    _inherit = 'hr.payslip'

    def compute_sheet(self):
        self.employee_id.sudo().write({
            "payslip_from": self.date_from,
            "payslip_to": self.date_to
        })

        return super(payslip, self).compute_sheet()
