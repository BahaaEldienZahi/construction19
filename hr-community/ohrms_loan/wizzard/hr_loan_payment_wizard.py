from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrLoanPaymentWizard(models.TransientModel):
    _name = 'hr.loan.payment.wizard'
    _description = 'HR Loan Payment Wizard'

    loan_id = fields.Many2one(
        'hr.loan',
        string='Loan',
        required=True,
        readonly=True
    )
    employee_id = fields.Many2one(
        related='loan_id.employee_id',
        string='Employee',
        readonly=True
    )
    due_amount = fields.Float(
        string='Due Amount',
        readonly=True,
        compute='_compute_due_amount'
    )
    payment_amount = fields.Float(
        string='Amount',
        required=True
    )
    payment_date = fields.Date(
        string='Payment Date',
        required=True,
        default=fields.Date.today
    )
    journal_id = fields.Many2one(
        'account.journal',
        string='Journal',
        required=True,
        domain=[('type', 'in', ['bank', 'cash'])]
    )
    memo = fields.Char(
        string='Memo / Note',
    )

    @api.depends('loan_id')
    def _compute_due_amount(self):
        for rec in self:
            if rec.loan_id:
                rec.due_amount = rec.loan_id.loan_amount

                if hasattr(rec.loan_id, 'loan_lines') and rec.loan_id.loan_lines:
                    paid_amount = sum(line.amount for line in rec.loan_id.loan_lines if line.paid)
                    rec.due_amount = rec.loan_id.loan_amount - paid_amount
            else:
                rec.due_amount = 0.0

    @api.onchange('loan_id')
    def _onchange_loan_id(self):
        if self.loan_id:
            # نستخدم due_amount المحسوب أعلاه
            self.payment_amount = self.due_amount

    @api.constrains('payment_amount')
    def _check_payment_amount(self):
        for rec in self:
            if rec.payment_amount > rec.loan_id.loan_amount:
                raise ValidationError(_('You cannot pay more than the loan amount!'))

    def button_confirm(self):
        self.ensure_one()

        if self.payment_amount <= 0:
            raise ValidationError(_('Payment amount must be greater than zero!'))

        if self.payment_amount > self.due_amount:
            raise ValidationError(_('You cannot pay more than the due amount!'))

        employee = self.loan_id.employee_id

        partner_id = False

        if hasattr(employee, 'address_home_id') and employee.address_home_id:
            partner_id = employee.address_home_id.id

        elif employee.user_id and employee.user_id.partner_id:
            partner_id = employee.user_id.partner_id.id

        if not partner_id:
            partner = self.env['res.partner'].search([
                ('name', '=', employee.name),
                ('company_id', 'in', [self.env.company.id, False])  # البحث في الشركة أو عام
            ], limit=1)

            if partner:
                partner_id = partner.id
                if hasattr(employee, 'address_home_id'):
                    employee.sudo().write({'address_home_id': partner.id})

        if not partner_id:
            partner = self.env['res.partner'].sudo().create({
                'name': employee.name,
                'company_id': self.env.company.id
            })
            partner_id = partner.id
            if hasattr(employee, 'address_home_id'):
                employee.sudo().write({'address_home_id': partner.id})
                # مفيش raise هنا خالص - كملنا عادي بالـ partner الجديد
        conf = self.env['hr.loan.conf'].search([], limit=1)

        if not conf or not conf.loan_account_id:
            raise ValidationError(
                _('Please configure the Loan Account in HR Loan Configuration first.')
            )
        payment_vals = {
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'partner_id': partner_id,
            'amount': self.payment_amount,
            'date': self.payment_date,
            'journal_id': self.journal_id.id,
            'ref': self.memo or _('Loan Payment: %s') % self.loan_id.name,
            'currency_id': self.env.company.currency_id.id,
            'destination_account_id': conf.loan_account_id.id,
        }

        payment = self.env['account.payment'].sudo().create(payment_vals)
        payment.action_post()

        self.loan_id.write({
            'cash_payment_ids': [(4, payment.id)],
            'state':'paid'
        })


        return {'type': 'ir.actions.act_window_close'}