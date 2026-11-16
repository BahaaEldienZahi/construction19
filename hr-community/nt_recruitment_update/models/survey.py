from odoo import fields, models, api


class survey(models.Model):
    _inherit = 'survey.survey'

    department_id=fields.Many2one('hr.department',string='Department')
    is_welcome_survey=fields.Boolean(string='welcome  Survey' ,default=False)

