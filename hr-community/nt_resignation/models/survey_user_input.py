from odoo import fields, models, api
from odoo.http import request


class SurveyUserInput(models.Model):
    _inherit = 'survey.user_input'

    employee_id = fields.Many2one('hr.employee', string='employee')

    @api.model_create_multi
    def create(self, vals):
        for val in vals:
            res = super(SurveyUserInput, self).create(val)
            if request.session.get('emp') and request.session.get('pid'):
                res.employee_id = request.session.get('emp')
                # rec = self.env['hr.resignation'].browse(request.session.get('pid'))
                # rec.write({'state': 'confirm'})
                request.session['emp'] = None
                request.session['pid'] = None
            return res
