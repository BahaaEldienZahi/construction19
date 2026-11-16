from odoo import api, fields, models


class BoardingStage(models.Model):
    _name = 'boarding.stage'
    _description = 'boarding stage'

    name = fields.Char(default='First', required=False, )
    responsible_id = fields.Many2one('hr.employee', string='Responsible', )
    user_id = fields.Many2one('res.users', string='User', related='responsible_id.user_id')
    department_id = fields.Many2one('hr.department', string='Department', related='responsible_id.department_id')
    sequence = fields.Integer(string="sequence", required=False, )
    help_desk_team = fields.Many2one('helpdesk.ticket.team')
    # team_id = fields.Many2one('helpdesk.team', store=True, tracking=True, default=False)

    category = fields.Many2one('helpdesk.category', domain="[('helpdesk_team_id', '=', help_desk_team)]")
    ticket_type_id = fields.Many2one('helpdesk.ticket.type', domain="[('helpdesk_team_ids', 'in', help_desk_team)]")

    description = fields.Text('ticket description')






