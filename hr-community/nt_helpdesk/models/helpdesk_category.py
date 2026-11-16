""" Initialize Helpdesk Category """

from odoo import fields, models


class HelpdeskCategory(models.Model):
    """
        Initialize Helpdisk Category:
         -
    """
    _name = 'helpdesk.category'
    _description = 'Helpdesk Category'
    _check_company_auto = True

    name = fields.Char(
        required=True,
        translate=True,
    )
    active = fields.Boolean(
        default=True, invisible=1
    )
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
    )
    parent_id = fields.Many2one(
        'helpdesk.category'
    )
    # helpdesk_department_id = fields.Many2one(
    #     'helpdesk.department'
    # )
    helpdesk_team_id = fields.Many2one(
        'helpdesk.ticket.team'
    )
