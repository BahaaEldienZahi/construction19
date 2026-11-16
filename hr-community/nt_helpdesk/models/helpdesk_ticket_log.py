from odoo import _, api, fields, models

LOG_PRIORITY = [
    ('0', 'Low priority'),
    ('1', 'Medium priority'),
    ('2', 'High priority'),
    ('3', 'Urgent'),
]


class HelpdeskTicketLog(models.Model):
    _name = 'helpdesk.ticket.log'
    _description = 'Helpdesk Ticket Log'

    ticket_id = fields.Many2one(comodel_name="helpdesk.ticket", readonly=True)
    ticket_name = fields.Char(string="Ticket Name", readonly=True)
    stage_id = fields.Many2one(comodel_name="helpdesk.ticket.stage", readonly=True)
    team_id = fields.Many2one('helpdesk.ticket.team', readonly=True)
    employee_id = fields.Many2one('hr.employee', readonly=True)
    user_id = fields.Many2one('res.users', string="User", readonly=True,)
    priority = fields.Selection(LOG_PRIORITY, string='Priority', default='0', readonly=True, tracking=True)
    helpdesk_area_id = fields.Many2one('helpdesk.area', store=True, string="Area")
    category_id = fields.Many2one('helpdesk.category', store=True, tracking=True, string="Category")
    ticket_type_id = fields.Many2one('helpdesk.ticket.type', tracking=True, string="Type")
    tag_ids = fields.Many2many('helpdesk.ticket.tag', tracking=True, string="tags")
    change = fields.Selection(string="Changes", readonly=True,
                              selection=[('create', 'Created Ticket'), ('change_stage', 'Change Stage'),
                                         ('change_department', 'Change Department'),
                                         ('change_team', 'Change Team'), ('change_assigned', 'Change Assigned'),
                                         ('change_priority', 'Change Priority'),
                                         ('change_area', 'Change Area'),
                                         ('change_category', 'Change Category'),
                                         ('change_type', 'Change Type'),
                                         ('change_tags', 'Change Tags'), ], required=False,)
