from odoo import fields, models, api
import werkzeug


class Survey(models.Model):
    _inherit = 'survey.survey'

    is_resignation = fields.Boolean('Resignation')
    is_resignation_exit = fields.Boolean('Exit Resignation')
    url = fields.Char('Exit Survey URL', compute="compute_exit_survey")


    def action_start_survey(self, answer=None):
        """ Open the website page with the survey form """
        for rec in self:
            rec.ensure_one()
            url = '%s?%s' % (
                self.get_start_url(), werkzeug.urls.url_encode({'answer_token': answer and answer.access_token or None}))
            return {
                'type': 'ir.actions.act_url',
                'name': "Start Survey",
                'target': 'new',
                'url': url,
            }

    def compute_exit_survey(self, answer=None):
        """ Open the website page with the survey form """
        for rec in self:
            rec.ensure_one()
            rec.url = self.env['ir.config_parameter'].sudo().get_param('web.base.url') + '%s?%s' % (
                self.get_start_url(),
                werkzeug.urls.url_encode({'answer_token': answer and answer.access_token or None}))
