from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from datetime import date
import datetime


class HelpdeskTicket(models.Model):
    """
        Inherit Helpdesk Ticket:
         -
    """
    _inherit = 'helpdesk.ticket'

    app_id = fields.Many2one('hr.applicant')

