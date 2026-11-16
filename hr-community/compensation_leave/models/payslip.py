from odoo import fields, models, api
from calendar import monthrange



class payslip(models.Model):
    _inherit = 'hr.payslip'

    amount_leave = fields.Float()
    amount_leave_2 = fields.Float()
    month_days = fields.Integer(compute='get_month_days', store=True)

    @api.depends('date_from')
    def get_month_days(self):
        """ Month Days """
        for rec in self:
            last_day = fields.Date.from_string(rec.date_from)
            rec.month_days = monthrange(last_day.year, last_day.month)[1]

    def compute_sheet(self):
        for record in self:
            leave_ids = self.env['hr.leave'].search([
                ('employee_id', '=', record.employee_id.id),
                ('request_date_from', '>=', record.date_from),
                ('request_date_from', '<=', record.date_to),
                ('state', 'in', ('validate', 'validate1')),
                ('holiday_status_id.to_be_compensation', '=', True),
            ])
            record.amount_leave = 0
            record.amount_leave_2 = 0

            day_value = record.contract_id.wage / 30

            for rec in leave_ids:
                if rec.compensation_type == 'money':
                    record.amount_leave += day_value * 2 * rec.number_of_days

                elif rec.compensation_type == 'leave_money':
                    record.amount_leave_2 += day_value * 1 * rec.number_of_days

            if record.amount_leave > 0 or record.amount_leave_2 > 0:

                record.input_line_ids.filtered(
                    lambda l: l.code in ['COMP_MONEY', 'COMP_LEAVE_MONEY']
                ).unlink()

                if record.amount_leave > 0:
                    self.env['hr.payslip.input'].create({
                        'name': 'Compensation Money',
                        'code': 'COMP_MONEY',
                        'amount': record.amount_leave,
                        'payslip_id': record.id,
                        'sequence': 10,
                        'contract_id': record.contract_id.id,
                    })

                if record.amount_leave_2 > 0:
                    self.env['hr.payslip.input'].create({
                        'name': 'Compensation Leave Money',
                        'code': 'COMP_LEAVE_MONEY',
                        'amount': record.amount_leave_2,
                        'payslip_id': record.id,
                        'sequence': 11,
                        'contract_id': record.contract_id.id,
                    })

        # res = super(payslip, self).compute_sheet()
        # return res

    def action_payslip_cancel(self):
        # if self.filtered(lambda slip: slip.state == 'done'):
        #     raise UserError(_("Cannot cancel a payslip that is done."))
        self.write({'state': 'cancel'})
        # self.mapped('payslip_run_id').action_close()
