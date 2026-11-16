from odoo import api, fields, models


class HelpdeskAttachment(models.Model):
    _name = 'helpdesk.attachment'
    _description = 'Helpdesk Attachment'

    ticket_id = fields.Many2one(comodel_name="helpdesk.ticket", string="Ticket", required=False, )
    attachment_id = fields.Many2many('ir.attachment', string="Attachment", tracking=True, required=True)
    date = fields.Datetime(string="Date", required=False, )
