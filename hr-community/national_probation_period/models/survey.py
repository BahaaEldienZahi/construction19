from odoo import fields, models, api
import werkzeug


class Survey(models.Model):
    _inherit = 'survey.survey'

    department_ids = fields.Many2many('hr.department', string='Department')
    is_emp_survey = fields.Boolean(string='Employee Survey', default=False)

    def action_start_survey(self, answer=None):
        """ Open the website page with the survey form """
        for rec in self:
            rec.ensure_one()
            url = '%s?%s' % (self.get_start_url(), werkzeug.urls.url_encode({'answer_token': answer and answer.access_token or None}))
            return {
                'type': 'ir.actions.act_url',
                'name': "Start Survey",
                'target': 'new',
                'url': url,
            }

