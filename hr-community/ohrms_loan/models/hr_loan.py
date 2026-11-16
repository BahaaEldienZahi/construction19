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
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import math
import logging

_logger = logging.getLogger(__name__)


class HrLoan(models.Model):
    """ Model for managing loan requests."""
    _name = 'hr.loan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Loan Request"

    @api.model
    def default_get(self, field_list):
        """ Function used to pass employee corresponding to current login user
            as default employee while creating new loan request
            :param field_list : Fields and values for the model hr.loan"""
        result = super(HrLoan, self).default_get(field_list)
        if result.get('user_id'):
            user_id = result['user_id']
        else:
            user_id = self.env.context.get('user_id', self.env.user.id)
        result['employee_id'] = self.env['hr.employee'].search(
            [('user_id', '=', user_id)], limit=1).id
        return result

    name = fields.Char(string="Loan Name", default="New", readonly=True,
                       help="Name of the loan")
    date = fields.Date(string="Date", default=fields.Date.today(),
                       readonly=True, help="Date of the loan request")
    employee_id = fields.Many2one('hr.employee', string="Employee",
                                  required=True, help="Employee Name")
    department_id = fields.Many2one('hr.department',
                                    related="employee_id.department_id",
                                    readonly=True,
                                    string="Department",
                                    help="The department to which the "
                                         "employee belongs.")
    installment = fields.Integer(string="No Of Installments", default=12,
                                 help="Number of installments")
    payment_date = fields.Date(string="Payment Start Date", required=True,
                               default=fields.Date.today(),
                               help="Date of the payment")
    loan_lines = fields.One2many('hr.loan.line', 'loan_id',
                                 string="Loan Line",
                                 help="Details of installment lines "
                                      "associated with the loan.",
                                 index=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 help="Company",
                                 default=lambda self: self.env.user.company_id)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  required=True, help="Currency",
                                  default=lambda self: self.env.user.
                                  company_id.currency_id)
    job_position = fields.Many2one('hr.job',
                                   related="employee_id.job_id",
                                   readonly=True, string="Job Position",
                                   help="Job position of the employee")
    loan_amount = fields.Float(string="Loan Amount", required=True,
                               help="Loan amount")
    total_amount = fields.Float(string="Total Amount", store=True,
                                readonly=True, compute='_compute_total_amount',
                                help="The total amount of the loan")
    balance_amount = fields.Float(string="Balance Amount", store=True,
                                  compute='_compute_total_amount',
                                  help="""The remaining balance amount of the 
                                  loan after deducting 
                                  the total paid amount.""")
    total_paid_amount = fields.Float(string="Total Paid Amount", store=True,
                                     compute='_compute_total_amount',
                                     help="The total amount that has been "
                                          "paid towards the loan.")
    state = fields.Selection(
        [('draft', 'Draft'), ('waiting_approval_1', 'Submitted'),
         ('approve', 'Approved'), ('refuse', 'Refused'), ('cancel', 'Canceled'),('paid','Paid'),('complete','Complete')
         ], string="State", default='draft', help="The current state of the "
                                                  "loan request.", copy=False)
    max_loan_amount = fields.Integer(string="Max.Loan Amount", compute='_compute_max_loan_amount', store=True)
    max_installment_amount = fields.Integer(string='Max. Installment Amount', compute='_compute_max_installment_amount',store=True)
    amount_to_be_deducted_from_salary =fields.Integer(string='Amount to be deducted from salary',compute='_compute_amount_to_be_deducted_from_salary',store=True)
    amount_to_be_deducted_from_annual_profit =fields.Integer(string='Amount to be deducted from annual profit',compute='_compute_amount_to_be_deducted_from_annual_profit',store=True)
    direct_payment_ids = fields.Many2many(
        'account.move',
        'hr_loan_account_move_rel',
        'loan_id', 'move_id',
        string='Direct Journal Entries',
        copy=False,
    )

    cash_payment_ids = fields.Many2many(
        'account.payment',
        'hr_loan_account_payment_rel',
        'loan_id', 'payment_id',
        string='Direct Cash/Bank Payments',
        copy=False,
    )
    installment_readonly = fields.Boolean(
        string='Installment Readonly',
        compute='_compute_installment_readonly',
        store=False
    )

    @api.depends('employee_id', 'loan_amount')
    def _compute_installment_readonly(self):
        for rec in self:
            wage = 0
            contract = rec.employee_id.contract_id
            if contract:
                wage = contract.wage
            rec.installment_readonly = rec.loan_amount > wage

    @api.onchange('loan_amount', 'employee_id')
    def _onchange_loan_amount_installment(self):
        for rec in self:
            wage = 0
            contract = rec.employee_id.contract_id
            if contract:
                wage = contract.wage

            if rec.loan_amount > wage:
                # حالة 1: السلفة أكبر من المرتب → ثابت 12
                rec.installment = 12
            else:
                # حالة 2: السلفة أقل → احسب أقل عدد أقساط يسدد بالكامل
                if rec.max_installment_amount and rec.max_installment_amount > 0:
                    min_installments = math.ceil(
                        rec.loan_amount / rec.max_installment_amount
                    )
                    rec.installment = max(1, min(min_installments, 12))
                else:
                    rec.installment = 12
    @api.onchange('installment')
    def _onchange_installment_validate(self):
        for rec in self:
            wage = 0
            contract = rec.employee_id.contract_id
            if contract:
                wage = contract.wage

            if rec.max_installment_amount and rec.max_installment_amount > 0:
                min_required = math.ceil(
                    rec.loan_amount / rec.max_installment_amount
                )
                if rec.installment < min_required:
                    rec.installment = min_required

            if rec.installment > 12:
                rec.installment = 12

    @api.depends('employee_id')
    def _compute_max_loan_amount(self):
        for rec in self:
            contract = self.env['hr.contract'].search([
                ('employee_id', '=', rec.employee_id.id),
                ('state', '=', 'open')
            ], limit=1)

            wage = contract.wage if contract else 0
            salary_based = wage * 3

            rec.max_loan_amount = min(150000, salary_based)

    @api.depends('loan_amount')
    def _compute_amount_to_be_deducted_from_salary(self):
        for rec in self:
            amount = rec.loan_amount / rec.installment
            rec.amount_to_be_deducted_from_salary =( amount if amount < rec.max_installment_amount else rec.max_installment_amount ) * rec.installment

    @api.depends('loan_amount')
    def _compute_amount_to_be_deducted_from_annual_profit(self):
        for rec in self :
            rec.amount_to_be_deducted_from_annual_profit = rec.loan_amount - rec.amount_to_be_deducted_from_salary

    @api.depends('employee_id')
    def _compute_max_installment_amount(self):
        for rec in self:
            wage = 0
            contract = rec.employee_id.contract_id
            if contract:
                wage = contract.wage

            rec.max_installment_amount = wage * 0.10

    @api.depends('loan_amount', 'max_installment_amount')
    def _compute_min_no_of_installments(self):
        for rec in self:
            if rec.max_installment_amount:
                rec.min_no_of_installments = math.ceil(
                rec.loan_amount / rec.max_installment_amount)
            else:
                rec.min_no_of_installments = 0

    @api.constrains('loan_amount')
    def _constraint_loan_amount(self):
        for rec in self:
            if rec.loan_amount > rec.max_loan_amount:
                raise ValidationError(
                    "Loan Amount cannot be greater than the maximum allowed loan amount."
                )

    @api.constrains('installment', 'loan_amount', 'employee_id')
    def _constraint_no_of_installments(self):
        for rec in self:
            if rec.installment > 12:
                raise ValidationError(
                    _("Number of installments cannot be bigger than 12.")
                )

    def _compute_total_amount(self):
        """ Compute total loan amount,balance amount and total paid amount"""
        total_paid = 0.0
        for loan in self:
            for line in loan.loan_lines:
                if line.paid:
                    total_paid += line.amount
            balance_amount = loan.loan_amount - total_paid
            loan.total_amount = loan.loan_amount
            loan.balance_amount = balance_amount
            loan.total_paid_amount = total_paid

    @api.model
    def create(self, values):
        """ Check whether any pending loan is for the employee and calculate
            the sequence
            :param values : Dictionary which contain fields and values"""
        loan_count = self.env['hr.loan'].search_count(
            [('employee_id', '=', values['employee_id']),
             ('state', '=', 'approve'),
             ('balance_amount', '!=', 0)])
        if loan_count:
            raise ValidationError(
                _("The Employee has already a pending installment"))
        else:
            values['name'] = self.env['ir.sequence'].get('hr.loan.seq') or ' '
            return super(HrLoan, self).create(values)

    def action_compute_installment(self):
        """This automatically create the installment the employee need to pay to
            company based on payment start date and the no of installments.
            """
        for loan in self:
            loan.loan_lines.unlink()
            date_start = datetime.strptime(str(loan.payment_date), '%Y-%m-%d')
            amount = loan.loan_amount / loan.installment
            for i in range(1, loan.installment + 1):
                self.env['hr.loan.line'].create({
                    'date': date_start,
                    'amount': amount if amount < loan.max_installment_amount else loan.max_installment_amount,
                    'employee_id': loan.employee_id.id,
                    'loan_id': loan.id})
                date_start = date_start + relativedelta(months=1)
            if self.amount_to_be_deducted_from_annual_profit > 0:
                self.env['hr.loan.line'].sudo().create({
                    'loan_id': loan.id,
                    'date': date_start,
                    'amount': self.amount_to_be_deducted_from_annual_profit,
                    'employee_id': loan.employee_id.id,
                    'payslip_id': False,})
            loan._compute_total_amount()
        return True

    def action_refuse(self):
        """ Function to reject loan request"""
        return self.write({'state': 'refuse'})

    def action_submit(self):
        """ Function to submit loan request"""
        self.write({'state': 'waiting_approval_1'})

    def action_cancel(self):
        """ Function to cancel loan request"""
        self.write({'state': 'cancel'})

    def action_register_payment(self):
        self.ensure_one()

        if self.loan_amount <= 0:
            raise UserError(_('لا يوجد مبلغ مستحق للدفع!'))

        return {
            'type': 'ir.actions.act_window',
            'name': 'Register Loan Payment',
            'res_model': 'hr.loan.payment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_loan_id': self.id,
                'default_payment_amount': self.loan_amount,
            }
        }
    def action_restructure_loan(self):
        """Open the wizard to pay from annual profit."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Restructuring Loan'),
            'res_model': 'hr.loan.restructure.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_active_id':self.id,
                'default_loan_id': self.id,
                'default_amount_to_pay': self.balance_amount,
                'default_memo': _('Loan Settlement via Annual Profit'),
            }
        }

    def action_approve(self):
        """ Function to approve loan request"""
        for data in self:
            if not data.loan_lines:
                raise ValidationError(_("Please Compute installment"))
            else:
                self.write({'state': 'approve'})

    def unlink(self):
        """ Function which restrict the deletion of approved or submitted
                loan request"""
        for loan in self:
            if loan.state not in ('draft', 'cancel'):
                raise UserError(_(
                    'You cannot delete a loan which is not in draft '
                    'or cancelled state'))
        return super(HrLoan, self).unlink()


class HrLoanLine(models.Model):
    """ Model for managing details of loan request installments"""
    _name = "hr.loan.line"
    _description = "Installment Line"

    date = fields.Date(string="Payment Date", required=True,
                       help="Date of the payment")
    employee_id = fields.Many2one('hr.employee', string="Employee",
                                  help="Employee")
    amount = fields.Float(string="Amount", required=True, help="Amount")
    paid = fields.Boolean(string="Paid", help="Indicates whether the "
                                              "installment has been paid.")
    loan_id = fields.Many2one('hr.loan', string="Loan Ref.",
                              help="Reference to the associated loan.")
    payslip_id = fields.Many2one('hr.payslip', string="Payslip Ref.",
                                 help="Reference to the associated "
                                      "payslip, if any.")