""" Initialize Helpdesk Stage """

from odoo import fields, models


class HelpdeskStage(models.Model):
    """
        Inherit Helpdesk Stage:
         -
    """
    _inherit = 'helpdesk.ticket.stage'

    hide_stage_from_ids = fields.Many2many(
        'res.users'
    )
    is_global = fields.Boolean(string='Is Global')
    is_close = fields.Boolean(string='Is Close')
    is_reopen = fields.Boolean(string='Is Re-Open')
    is_to_check = fields.Boolean(string='Is To-Check')
    helpdesk_team_id = fields.Many2one(
        'helpdesk.ticket.team'
    )

