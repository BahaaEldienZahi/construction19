# -*- coding: utf-8 -*-

from odoo import models, fields


class HelpdeskTicketType(models.Model):
    _name = 'helpdesk.ticket.type'
    _description = 'Helpdesk Ticket Type'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    helpdesk_team_ids = fields.Many2many(
        'helpdesk.ticket.team', string='Teams'
    )
