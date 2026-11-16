# -*- coding: utf-8 -*-
#############################################################################
#    A part of Open HRMS Project <https://www.openhrms.com>
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import models


class HrPayslip(models.Model):
    """ Extends the 'hr.payslip' model to include
    additional functionality related to employee loans."""
    _inherit = 'hr.payslip'

    def get_inputs(self, contract_ids, date_from, date_to):
        res = super(HrPayslip, self).get_inputs(contract_ids, date_from, date_to)
        contract = self.env['hr.contract'].browse(contract_ids[0].id) if contract_ids else False
        employee_id = contract.employee_id if contract else self.employee_id

        loan_ids = self.env['hr.loan'].search([
            ('employee_id', '=', employee_id.id),
            ('state', '=', 'approve')
        ])

        for loan in loan_ids:
            for loan_line in loan.loan_lines:
                if date_from <= loan_line.date <= date_to and not loan_line.paid:
                    found = False
                    for result in res:
                        if result.get('code') == 'LO':
                            result['amount'] = loan_line.amount
                            result['loan_line_id'] = loan_line.id
                            found = True
                            break
                    if not found:
                        res.append({
                            'name': 'Loan',
                            'code': 'LO',
                            'amount': loan_line.amount,
                            'contract_id': contract.id if contract else False,
                            'loan_line_id': loan_line.id,
                        })
        return res



    def action_payslip_done(self):
        for line in self.input_line_ids:
            if line.loan_line_id:
                line.loan_line_id.paid = True
                line.loan_line_id.loan_id._compute_total_amount()
        return super(HrPayslip, self).action_payslip_done()


    def action_compute_sheet(self):
        for payslip in self:
            loan_ids = self.env['hr.loan'].search([
                ('employee_id', '=', payslip.employee_id.id),
                ('state', '=', 'approve'),
            ])
            total_loan = 0.0
            loan_line_id = False
            for loan in loan_ids:
                for loan_line in loan.loan_lines:
                    if (payslip.date_from <= loan_line.date <= payslip.date_to
                            and not loan_line.paid):
                        total_loan += loan_line.amount
                        loan_line_id = loan_line.id
            payslip.input_line_ids.filtered(lambda l: l.code == 'LO').unlink()
            if total_loan:
                self.env['hr.payslip.input'].create({
                    'payslip_id': payslip.id,
                    'name': 'Loan',
                    'code': 'LO',
                    'amount': total_loan,
                    'contract_id': payslip.contract_id.id,
                    'loan_line_id': loan_line_id,
                })
        return super(HrPayslip, self).action_compute_sheet()