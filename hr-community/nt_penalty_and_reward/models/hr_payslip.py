from odoo import fields, models, api


class payslip(models.Model):
    _inherit = 'hr.payslip'

    def compute_sheet(self):
        for rec in self:
            rec.employee_id.sudo().write({
                "payslip_from": rec.date_from,
                "payslip_to": rec.date_to
            })

        return super(payslip, self).compute_sheet()
