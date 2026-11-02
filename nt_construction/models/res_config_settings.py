from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    construction_revenue_account_id = fields.Many2one(
        related='company_id.construction_revenue_account_id', readonly=False)
    construction_retention_account_id = fields.Many2one(
        related='company_id.construction_retention_account_id', readonly=False)
    construction_advance_account_id = fields.Many2one(
        related='company_id.construction_advance_account_id', readonly=False)
    construction_sale_tax_id = fields.Many2one(
        related='company_id.construction_sale_tax_id', readonly=False)
    construction_withholding_tax_id = fields.Many2one(
        related='company_id.construction_withholding_tax_id', readonly=False)
    construction_advance_tax_id = fields.Many2one(
        related='company_id.construction_advance_tax_id', readonly=False)
    construction_escalation_vat = fields.Boolean(
        related='company_id.construction_escalation_vat', readonly=False)
    construction_subcontract_cost_account_id = fields.Many2one(
        related='company_id.construction_subcontract_cost_account_id', readonly=False)
    construction_retention_payable_account_id = fields.Many2one(
        related='company_id.construction_retention_payable_account_id', readonly=False)
    construction_purchase_tax_id = fields.Many2one(
        related='company_id.construction_purchase_tax_id', readonly=False)
    construction_purchase_withholding_tax_id = fields.Many2one(
        related='company_id.construction_purchase_withholding_tax_id', readonly=False)
    construction_divergence_threshold = fields.Float(
        related='company_id.construction_divergence_threshold', readonly=False)
