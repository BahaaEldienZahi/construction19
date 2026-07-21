# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class NcrReport(models.Model):
    _name = 'ncr.report'
    _description = 'Non-Conformance Report (NCR)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'reported_date desc, id desc'

    name = fields.Char(default=lambda self: _('New'), readonly=True, copy=False)
    project_id = fields.Many2one(
        'project.project', string='Project', required=True,
        domain=[('is_construction_project', '=', True)], tracking=True,
    )
    inspection_id = fields.Many2one(
        'work.inspection', string='Source Inspection',
        domain="["project_id', '=', project_id]",
        help='Link to the WIR/MIR that raised this NCR',
    )

    description = fields.Text(string='Description of Non-Conformance', required=True)
    severity = fields.Selection([
        ('minor', 'Minor'),
        ('major', 'Major'),
        ('critical', 'Critical'),
    ], string='Severity', default='minor', required=True, tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Open'),
        ('investigation', 'Under Investigation'),
        ('corrective_action', 'Corrective Action'),
        ('verified', 'Verified'),
        ('closed', 'Closed'),
    ], string='Status', default='draft', required=True, copy=False, tracking=True)

    reported_date = fields.Date(string='Reported Date', default=fields.Date.context_today, required=True)
    reporter_id = fields.Many2one('res.users', string='Reported By', default=lambda self: self.env.user)
    responsible_id = fields.Many2one('res.partner', string='Responsible Party')

    root_cause = fields.Text(string='Root Cause Analysis')
    corrective_action = fields.Text(string='Corrective Action')
    preventive_action = fields.Text(string='Preventive Action')

    closure_date = fields.Date(string='Closure Date', copy=False)
    verified_by = fields.Many2one('res.users', string='Verified By')
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('ncr.report') or _('New')
        return super().create(vals_list)

    def action_open(self):
        self.write({'state': 'open'})

    def action_investigate(self):
        self.write({'state': 'investigation'})

    def action_corrective(self):
        self.write({'state': 'corrective_action'})

    def action_verify(self):
        self.write({'state': 'verified', 'verified_by': self.env.user.id})

    def action_close(self):
        self.write({'state': 'closed', 'closure_date': fields.Date.context_today(self)})

    def action_reset_draft(self):
        self.write({'state': 'draft'})
