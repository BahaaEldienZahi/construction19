from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    bank_journal = fields.Many2one('account.journal', string='Bank Journal', )
    cash_journal = fields.Many2one('account.journal', string='Cash Journal', )

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        bank_journal = params.get_param('national_employee.bank_journal', default=False)
        cash_journal = params.get_param('national_employee.cash_journal', default=False)
        if bank_journal:
            res.update(
                bank_journal=int(bank_journal),
            )
        if cash_journal:
            res.update(
                cash_journal=int(cash_journal),
            )
        return res

    def set_values(self):
        res = super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('national_employee.bank_journal',
                                                         self.bank_journal.id)
        self.env['ir.config_parameter'].sudo().set_param('national_employee.cash_journal',
                                                         self.cash_journal.id)
        return res
