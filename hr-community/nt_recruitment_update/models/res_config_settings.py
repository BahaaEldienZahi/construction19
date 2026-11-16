from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    acceptance_mail = fields.Integer(config_parameter='nt_recruitment_update.acceptance_mail')

    recruitment_account_receivable_id = fields.Many2one('account.account',
                                                        domain="[('account_type', '=', 'asset_receivable'), ('deprecated', '=', False)]",
                                                        config_parameter="ResConfigSettings.recruitment_account_receivable")
    recruitment_account_payable_id = fields.Many2one('account.account',
                                                     domain="[('account_type', '=', 'liability_payable'), ('deprecated', '=', False)]",
                                                     config_parameter="ResConfigSettings.recruitment_account_payable")
