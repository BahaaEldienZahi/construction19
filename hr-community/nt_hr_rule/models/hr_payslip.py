from odoo import fields, models, api
from calendar import monthrange
import logging
_logger = logging.getLogger(__name__)


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def _get_reward_total(self, slip):

        employee = slip.employee_id
        contract = slip.contract_id
        date_from = slip.date_from
        date_to   = slip.date_to

        if not employee or not contract or not date_from:
            return 0.0

        month_days = monthrange(date_from.year, date_from.month)[1]
        daily_wage = (contract.wage or 0.0) / month_days

        total = 0.0
        for pr in employee.pr_ids:
            if pr.state != 'approve':
                continue
            if pr.start_date > date_to or pr.end_date < date_from:
                continue
            for reward_line in pr.employee_reward_ids:
                if reward_line.payment_method == 'money':
                    total += reward_line.amount_money or 0.0
                elif reward_line.payment_method == 'day':
                    total += (reward_line.amount_day or 0.0) * daily_wage

        return total

    def action_compute_sheet(self):
        for slip in self:
            if not slip.contract_id:
                continue
            if slip.contract_id.donot_tax_bracket:
                slip.contract_id.monthly_additions = 0.0
                continue

            inputs_total = sum(
                line.amount for line in slip.input_line_ids
                if (line.amount or 0) > 0
            )
            other_allowance = slip.contract_id.other_allowance
            profits = slip.contract_id.profits
            vacation_allowance = slip.contract_id.vacation_allowance

            reward_total = self._get_reward_total(slip)

            additions = inputs_total + reward_total + other_allowance + profits + vacation_allowance

            slip.contract_id.sudo().write({'monthly_additions': additions})

        return super().action_compute_sheet()

    def action_payslip_done(self):
        result = super().action_payslip_done()
        for slip in self:
            if not slip.contract_id:
                continue
            slip.contract_id.sudo().write({'monthly_additions': 0.0})
            print(slip.contract_id.monthly_additions, 'after super')
        return result

