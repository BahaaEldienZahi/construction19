""" Initialize Hr Job """

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class HrJob(models.Model):
    """
        Inherit Hr Job:
         -
    """
    _inherit = 'hr.job'

    no_of_recruitment = fields.Integer(string='Target', copy=False,
        help='Number of new employees you expect to recruit.', default=0)
    job_requirements = fields.Text()
    recruitment_team_id = fields.Many2one(
        'recruitment.team',
    )
