# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SiteDailyReport(models.Model):
    """التقرير اليومي للموقع (السركي): تسجيل يومي للعمالة والمعدات وأحوال
    الطقس وملاحظات الموقع، وتسجيل كميات الإنجاز الفعلي على بنود الـ BOQ
    في نفس اليوم كأساس لمستخلصات الكميات (Quantity-based billing)."""

    _name = 'site.daily.report'
    _description = 'Site Daily Report (Sarky)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(default=lambda self: _('New'), readonly=True, copy=False)
    project_id = fields.Many2one(
        'project.project', string='Project', required=True,
        domain=[('is_construction_project', '=', True)], tracking=True,
    )
    company_id = fields.Many2one(related='project_id.company_id', store=True, readonly=True)
    date = fields.Date(default=fields.Date.context_today, required=True, tracking=True)
    user_id = fields.Many2one('res.users', string='Site Engineer', default=lambda self: self.env.user)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
    ], default='draft', required=True, copy=False, tracking=True)

    weather = fields.Selection([
        ('clear', 'Clear'),
        ('cloudy', 'Cloudy'),
        ('rain', 'Rain'),
        ('sandstorm', 'Sandstorm / Khamaseen'),
        ('other', 'Other'),
    ], string='Weather', default='clear')

    manpower_ids = fields.One2many('site.daily.report.manpower', 'report_id', string='Manpower')
    equipment_ids = fields.One2many('site.daily.report.equipment', 'report_id', string='Equipment')
    progress_ids = fields.One2many(
        'boq.line.progress', 'daily_report_id', string='Quantities Executed Today',
    )

    total_manpower_count = fields.Integer(compute='_compute_totals', store=True)
    total_equipment_hours = fields.Float(compute='_compute_totals', store=True)
    total_amount_executed_today = fields.Monetary(
        string="Today's Executed Value", currency_field='currency_id',
        compute='_compute_totals', store=True,
    )
    currency_id = fields.Many2one(related='project_id.construction_currency_id', readonly=True)

    site_notes = fields.Text(string='Site Notes / Issues')

    _sql_constraints = [
        ('name_uniq', 'unique(name, company_id)', 'Daily report reference must be unique per company!'),
        ('project_date_uniq', 'unique(project_id, date)',
         'A daily report already exists for this project and date.'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('site.daily.report') or _('New')
        return super().create(vals_list)

    @api.depends('manpower_ids.headcount', 'equipment_ids.hours_worked',
                 'progress_ids.quantity_executed', 'progress_ids.boq_line_id.unit_price')
    def _compute_totals(self):
        for rec in self:
            rec.total_manpower_count = sum(rec.manpower_ids.mapped('headcount'))
            rec.total_equipment_hours = sum(rec.equipment_ids.mapped('hours_worked'))
            rec.total_amount_executed_today = sum(
                p.quantity_executed * p.boq_line_id.unit_price for p in rec.progress_ids
            )

    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Only draft reports can be confirmed.'))
        self.write({'state': 'confirmed'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})


class SiteDailyReportManpower(models.Model):
    _name = 'site.daily.report.manpower'
    _description = 'Site Daily Report - Manpower Line'

    report_id = fields.Many2one('site.daily.report', required=True, ondelete='cascade', index=True)
    project_id = fields.Many2one(related='report_id.project_id', store=True)
    trade = fields.Selection([
        ('foreman', 'Foreman'),
        ('mason', 'Mason'),
        ('carpenter', 'Carpenter'),
        ('steel_fixer', 'Steel Fixer'),
        ('electrician', 'Electrician'),
        ('plumber', 'Plumber'),
        ('painter', 'Painter'),
        ('general_labor', 'General Labor'),
        ('other', 'Other'),
    ], string='Trade', required=True, default='general_labor')
    is_subcontractor = fields.Boolean(string='Subcontractor Crew')
    subcontract_agreement_id = fields.Many2one(
        'subcontract.agreement', string='Subcontract',
        domain="[('project_id', '=', project_id)]",
    )
    headcount = fields.Integer(string='Headcount', required=True, default=1)
    hours = fields.Float(string='Hours Worked', default=8.0)
    note = fields.Char(string='Note')


class SiteDailyReportEquipment(models.Model):
    _name = 'site.daily.report.equipment'
    _description = 'Site Daily Report - Equipment Line'

    report_id = fields.Many2one('site.daily.report', required=True, ondelete='cascade', index=True)
    project_id = fields.Many2one(related='report_id.project_id', store=True)
    equipment_name = fields.Char(string='Equipment', required=True)
    equipment_type = fields.Selection([
        ('owned', 'Company Owned'),
        ('rented', 'Rented'),
    ], string='Type', default='owned')
    count = fields.Integer(string='Count', default=1)
    hours_worked = fields.Float(string='Hours Worked')
    hours_idle = fields.Float(string='Hours Idle')
    idle_reason = fields.Char(string='Idle Reason')