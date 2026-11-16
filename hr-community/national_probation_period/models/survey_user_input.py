from odoo import fields, models, api
from odoo.http import request


class survey(models.Model):
    _inherit = 'survey.user_input'

    employee_id = fields.Many2one('hr.employee', string='employee')
    is_emp_survey = fields.Boolean(string='Employee Survey', default=False)

    @api.model_create_multi
    def create(self, vals):
        for val in vals:
            res = super(survey, self).create(val)
            if request.session.get('emp') and request.session.get('pid'):
                res.employee_id = request.session.get('emp')
                rec = self.env['employee.probation.period'].browse(request.session.get('pid'))
                # rec.write({'state': 'confirm'})
                request.session['emp'] = None
                request.session['pid'] = None
            return res
