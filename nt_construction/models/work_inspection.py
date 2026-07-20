# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class WorkInspection(models.Model):
    """طلب فحص أعمال — Work Inspection Request (WIR / MIR)"""
    _name = 'work.inspection'
    _description = 'Work Inspection Request (WIR/MIR)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'inspection_date desc, id desc'

    name = fields.Char(default=lambda self: _('New'), readonly=True, copy=False)
    project_id = fields.Many2one(
        'project.project', string='Project', required=True,
        domain=[('is_construction_project', '=', True)], tracking=True,
    )
    company_id = fields.Many2one(related='project_id.company_id', store=True, readonly=True)
    date = fields.Date(default=fields.Date.context_today, required=True)

    inspection_type = fields.Selection([
        ('wir', 'Work Inspection Request (WIR)'),
        ('mir', 'Material Inspection Request (MIR)'),
        ('other', 'Other'),
    ], string='Type', default='wir', required=True)

    inspection_date = fields.Date(string='Inspection Date', tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('inspected', 'Inspected'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', required=True, copy=False, tracking=True)

    boq_line_ids = fields.Many2many(
        'boq.line', 'work_inspection_boq_line_rel',
        'inspection_id', 'boq_line_id', string='Related BOQ Lines',
        domain="[('project_id', '=', project_id), ('is_group', '=', False)]",
    )
    description = fields.Text(string='Scope of Inspection', required=True)
    location = fields.Char(string='Location / Area')
    inspector_id = fields.Many2one('res.users', string='Inspector')
    inspection_result = fields.Text(string='Inspection Result')
    is_conforming = fields.Boolean(string='Conforming', tracking=True)
    rejection_reason = fields.Text(string='Rejection Reason', copy=False)
    attachment_ids = fields.Many2many(
        'ir.attachment', string='Attachments',
        help='صور ووثائق الفحص',
    )

    _sql_constraints = [
        ('name_uniq', 'unique(name, company_id)', 'Inspection reference must be unique per company!'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('work.inspection') or _('New')
        return super().create(vals_list)

    def action_submit(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Only draft inspections can be submitted.'))
        self.write({'state': 'submitted'})

    def action_inspect(self):
        for rec in self:
            if rec.state != 'submitted':
                raise UserError(_('Only submitted inspections can be inspected.'))
        self.write({'state': 'inspected'})

    def action_approve(self):
        for rec in self:
            if rec.state != 'inspected':
                raise UserError(_('Only inspected items can be approved.'))
        self.write({'state': 'approved', 'is_conforming': True})

    def action_reject(self):
        self.write({'state': 'rejected', 'is_conforming': False})

    def action_reset_draft(self):
        self.write({'state': 'draft', 'is_conforming': False, 'rejection_reason': False})
