from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    # ---- client side (certificate invoices, advance, retention) — DECISIONS S12-S14
    construction_revenue_account_id = fields.Many2one(
        'account.account', check_company=True,
        help='Income account of certified work and escalation. Empty: the sales journal default.')
    construction_retention_account_id = fields.Many2one(
        'account.account', string='Retention Receivable Account', check_company=True,
        help='Debited by the retention deducted on each client certificate, credited on release.')
    construction_advance_account_id = fields.Many2one(
        'account.account', string='Customer Advances Account', check_company=True,
        help='Liability credited by the advance invoice, debited by advance recovery on certificates.')
    construction_sale_tax_id = fields.Many2one(
        'account.tax', string='VAT on Certificates', check_company=True,
        domain=[('type_tax_use', '=', 'sale')],
        help='Applied to the gross work value and escalation of the period (S12).')
    construction_withholding_tax_id = fields.Many2one(
        'account.tax', string='Withholding Tax on Certificates', check_company=True,
        domain=[('type_tax_use', '=', 'sale')],
        help='Default withholding tax (a negative tax) on the gross work value (S13). Overridable per project.')
    construction_advance_tax_id = fields.Many2one(
        'account.tax', string='VAT on Advance Invoices', check_company=True,
        domain=[('type_tax_use', '=', 'sale')],
        help='Tax of the advance invoice; also applied negatively on advance recovery (S14). Empty: none.')
    construction_escalation_vat = fields.Boolean(
        string='VAT on Escalation', default=True,
        help='PROVISIONAL (DECISIONS P2): escalation is part of the VAT base.')

    # ---- subcontractor side (subcontractor certificates → vendor bills)
    construction_subcontract_cost_account_id = fields.Many2one(
        'account.account', string='Subcontract Cost Account', check_company=True,
        help='Expense account of subcontractor certificates. Empty: the purchase journal default.')
    construction_retention_payable_account_id = fields.Many2one(
        'account.account', string='Retention Payable Account', check_company=True,
        help='Liability credited by the retention withheld from subcontractors.')
    construction_purchase_tax_id = fields.Many2one(
        'account.tax', string='VAT on Subcontractor Bills', check_company=True,
        domain=[('type_tax_use', '=', 'purchase')])
    construction_purchase_withholding_tax_id = fields.Many2one(
        'account.tax', string='Withholding Tax on Subcontractor Bills', check_company=True,
        domain=[('type_tax_use', '=', 'purchase')])

    # ---- dashboards (UX_SPEC Q1)
    construction_divergence_threshold = fields.Float(
        string='Executed vs Certified Alert (points)', default=10.0,
        help='Project cards turn orange/red when executed % and certified % differ by more than this.')
