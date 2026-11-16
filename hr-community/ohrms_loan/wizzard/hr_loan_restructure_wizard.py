from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrLoanRestructureWizard(models.TransientModel):
    _name = 'hr.loan.restructure.wizard'
    _description = 'Restructure Loan (Pay from Profit)'

    loan_id = fields.Many2one(
        'hr.loan',
        string='Loan',
        required=True,
        readonly=True
    )
    balance_amount = fields.Float(
        string='Remaining Amount',
        readonly=True,
        related='loan_id.balance_amount'
    )
    date = fields.Date(
        string='Date',
        required=True,
        default=fields.Date.today
    )
    amount_to_pay = fields.Float(
        string='Amount To Pay',
        required=True,
        help='The amount to deduct from annual profit.'
    )
    account_id = fields.Many2one(
        'account.account',
        string='Account',
        required=True,
        help='Select the Annual Profit Account (Source Account).'
    )
    journal_id = fields.Many2one(
        'account.journal',
        string='Journal',
        required=True,
        domain=[('type', '=', 'general')],
        help='Journal to make the accounting entry.'
    )
    memo = fields.Char(
        string='Memo'
    )

    # ── Installment lines ──────────────────────────────────────────────────
    line_ids = fields.One2many(
        'hr.loan.restructure.wizard.line',
        'wizard_id',
        string='Installment Lines'
    )
    select_all = fields.Boolean(string='Select All', default=False, store=False)

    # ── Onchange helpers ───────────────────────────────────────────────────
    @api.onchange('loan_id')
    def _onchange_loan_id(self):
        if self.loan_id:
            self.amount_to_pay = self.loan_id.balance_amount

    @api.onchange('select_all')
    def _onchange_select_all(self):
        for rec in self:
            for line in rec.line_ids:
                line.is_selected = rec.select_all
                line.pay_amount = line.amount if rec.select_all else 0.0
            selected = rec.line_ids.filtered(lambda l: l.is_selected)
            rec.amount_to_pay = sum(selected.mapped('pay_amount'))

    @api.onchange('line_ids', 'line_ids.is_selected', 'line_ids.pay_amount')
    def _onchange_total_amount(self):
        for wiz in self:
            selected = wiz.line_ids.filtered(lambda l: l.is_selected)
            wiz.amount_to_pay = sum(selected.mapped('pay_amount'))

    # ── default_get: populate lines from unpaid installments ──────────────
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_id = self._context.get('default_loan_id') or self._context.get('active_id')

        if active_id and 'line_ids' in fields_list:
            loan = self.env['hr.loan'].browse(active_id)
            line_values = []
            for loan_line in loan.loan_lines.filtered(lambda l: not l.paid).sorted('date'):
                line_values.append((0, 0, {
                    'loan_line_id': loan_line.id,
                    'is_selected': False,
                    'pay_amount': 0.0,
                }))
            res['line_ids'] = line_values

        return res


    def action_restructure(self):
        self.ensure_one()

        selected_lines = self.line_ids.filtered(lambda l: l.is_selected)
        if not selected_lines:
            raise ValidationError(_("Please select at least one installment line to pay."))

        # Fallback لو pay_amount وصل 0 بسبب onchange
        for wl in selected_lines:
            if wl.pay_amount <= 0:
                wl.pay_amount = wl.loan_line_id.amount

        total = sum(selected_lines.mapped('pay_amount'))

        if total > self.loan_id.balance_amount + 0.001:
            raise ValidationError(_("Total amount to pay cannot exceed the remaining loan balance!"))

        # ── Resolve partner ────────────────────────────────────────────────
        conf = self.env['hr.loan.conf'].search([], limit=1)
        if not conf or not conf.loan_account_id:
            raise ValidationError(
                _('Please configure Loan Account in HR Loan Configuration settings.')
            )
        loan_account_id = conf.loan_account_id.id

        employee = self.loan_id.employee_id
        partner_id = False

        if hasattr(employee, 'address_home_id') and employee.address_home_id:
            partner_id = employee.address_home_id.id
        elif employee.user_id and employee.user_id.partner_id:
            partner_id = employee.user_id.partner_id.id

        if not partner_id:
            partner = self.env['res.partner'].search([
                ('name', '=', employee.name),
                ('company_id', 'in', [self.env.company.id, False])
            ], limit=1)
            if partner:
                partner_id = partner.id
                if hasattr(employee, 'address_home_id'):
                    employee.sudo().write({'address_home_id': partner.id})

        if not partner_id:
            partner = self.env['res.partner'].sudo().create({
                'name': employee.name,
                'company_id': self.env.company.id,
            })
            partner_id = partner.id
            raise ValidationError(
                _('Cannot find a Partner for employee %s.\n'
                  'Please set a Home Address in the Employee form or link a User.') % employee.name
            )

        # ── Journal Entry (same logic as original action_restructure) ──────
        move_vals = {
            'date': self.date,
            'journal_id': self.journal_id.id,
            'ref': self.memo or _('Restructure Loan: %s') % self.loan_id.name,
            'line_ids': [
                (0, 0, {
                    'account_id': self.account_id.id,
                    'debit': total,
                    'credit': 0.0,
                    'partner_id': partner_id,
                    'name': self.memo or _('Loan Settlement from Profit'),
                }),
                (0, 0, {
                    'account_id': int(loan_account_id),
                    'debit': 0.0,
                    'credit': total,
                    'partner_id': partner_id,
                    'name': self.memo or _('Loan Settlement from Profit'),
                }),
            ],
        }
        move = self.env['account.move'].sudo().create(move_vals)
        move.action_post()

        self.loan_id.write({'direct_payment_ids': [(4, move.id)]})
        for wl in selected_lines:
            loan_line = wl.loan_line_id
            pay_amount = wl.pay_amount

            if pay_amount <= 0:
                continue

            if pay_amount >= loan_line.amount:
                loan_line.sudo().write({'paid': True})

        self.loan_id._compute_total_amount()
        if self.loan_id.balance_amount <= 0.001:
            self.loan_id.write({'state': 'complete'})
        return {'type': 'ir.actions.act_window_close'}


# ── Wizard Line ────────────────────────────────────────────────────────────────
class HrLoanRestructureWizardLine(models.TransientModel):
    _name = 'hr.loan.restructure.wizard.line'
    _description = 'Restructure Wizard - Installment Line'

    wizard_id = fields.Many2one(
        'hr.loan.restructure.wizard',
        string='Wizard',
        ondelete='cascade'
    )
    loan_line_id = fields.Many2one(
        'hr.loan.line',
        string='Installment',
        required=True
    )
    is_selected = fields.Boolean(string='Select', default=False)

    # Display fields (related / readonly)
    date = fields.Date(
        related='loan_line_id.date',
        string='Payment Date',
        readonly=True
    )
    employee_id = fields.Many2one(
        related='loan_line_id.employee_id',
        string='Employee',
        readonly=True
    )
    amount = fields.Float(
        related='loan_line_id.amount',
        string='Installment Amount',
        readonly=True
    )

    # Editable pay amount
    pay_amount = fields.Float(string='Pay Now', default=0.0)

    @api.onchange('is_selected')
    def _onchange_is_selected(self):
        for rec in self:
            rec.pay_amount = rec.amount if rec.is_selected else 0.0