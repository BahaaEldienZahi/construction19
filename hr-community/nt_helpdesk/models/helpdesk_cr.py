from odoo import api, fields, models


class HelpdeskCr(models.Model):
    _name = 'helpdesk.cr'
    _description = 'Helpdesk CR'
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']


    name = fields.Char(string='Name')
    partner_id = fields.Many2one('res.partner', string='Customer')
    ticket_id = fields.Many2one('helpdesk.ticket', string="Ticket")
    project_id = fields.Many2one('project.project', domain="[('partner_id', '=', partner_id)]", string='Project')


