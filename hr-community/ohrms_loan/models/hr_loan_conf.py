from odoo import fields, models, _


class HrLoanConf(models.Model):
    """Extends the 'hr.employee' model to include loan_count."""
    _name = "hr.loan.conf"

    loan_account_id = fields.Many2one(
        'account.account',
        string='Loan Account',
        required=True,
        help='Select the Annual Profit Account (Source Account).'
    )
    loan_journal_id = fields.Many2one(
        'account.journal',
        string='Journal',
        required=True,
        domain=[('type', '=', 'general')],
        help='Journal to make the accounting entry.'
    )