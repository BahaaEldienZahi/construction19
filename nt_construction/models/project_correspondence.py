# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProjectCorrespondence(models.Model):
    """المراسلات — Site Letters & Correspondence"""
    _name = 'project.correspondence'
    _description = 'Project Correspondence / Letters'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(default=lambda self: _('New'), readonly=True, copy=False)
    project_id = fields.Many2one(
        'project.project', string='Project', required=True,
        domain=[('is_construction_project', '=', True)], tracking=True,
    )
    company_id = fields.Many2one(related='project_id.company_id', store=True, readonly=True)
    date = fields.Date(default=fields.Date.context_today, required=True, tracking=True)

    direction = fields.Selection([
        ('incoming', 'Incoming'),
        ('outgoing', 'Outgoing'),
    ], string='Direction', default='outgoing', required=True, tracking=True)

    correspondence_type = fields.Selection([
        ('letter', 'Letter'),
        ('email', 'Email'),
        ('minutes', 'Minutes of Meeting'),
        ('notice', 'Notice / Warning'),
        ('transmittal', 'Transmittal'),
        ('claim', 'Claim / EOT'),
        ('other', 'Other'),
    ], string='Type', default='letter', required=True)

    reference_number = fields.Char(string='Reference Number')
    subject = fields.Char(string='Subject', required=True)
    sender_id = fields.Many2one('res.partner', string='From', tracking=True)
    recipient_id = fields.Many2one('res.partner', string='To', tracking=True)
    body = fields.Text(string='Content')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent / Received'),
        ('responded', 'Responded'),
        ('closed', 'Closed'),
    ], string='Status', default='draft', required=True, copy=False, tracking=True)

    response_required = fields.Boolean(string='Response Required')
    response_deadline = fields.Date(string='Response Deadline')
    response_id = fields.Many2one('project.correspondence', string='Response To', ondelete='set null')
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')

    _sql_constraints = [
        ('name_uniq', 'unique(name, company_id)', 'Correspondence reference must be unique per company!'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('project.correspondence') or _('New')
        return super().create(vals_list)

    def action_mark_sent(self):
        self.write({'state': 'sent'})

    def action_close(self):
        self.write({'state': 'closed'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})
