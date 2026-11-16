from odoo import models, fields, api


class ProbationConfigSettings(models.TransientModel):
    _name = 'probation.config.settings'
    _inherit = 'res.config.settings'

    num_day_before = fields.Integer(string="", required=False,store=True )

    @api.model
    def get_values(self):
        res = super(ProbationConfigSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        num_day_before = params.get_param('national_probation_period.num_day_before', default=False)

        if num_day_before:
            res.update(
                num_day_before=int(num_day_before),
            )

        return res

    def set_values(self):
        res = super(ProbationConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('national_probation_period.num_day_before',
                                                         self.num_day_before)

        return res
