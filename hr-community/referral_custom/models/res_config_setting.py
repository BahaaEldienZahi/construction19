from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    amount = fields.Float(config_parameter='referral_custom.amount')
    memo = fields.Char(string="Memo", config_parameter='referral_custom.memo')

