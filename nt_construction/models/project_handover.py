# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProjectHandover(models.Model):
    """التسليم الابتدائي والنهائي للمشروع: يتابع تاريخ التسليم الابتدائي،
    فترة الصيانة (Defects Liability Period)، قائمة الملاحظات (Punch/Snag List)،
    والإفراج التدريجي عن الضمان لحد التسليم النهائي وإغلاق المشروع."""

    _name = 'project.handover'
    _description = 'Project Handover / Delivery Certificate'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(default=lambda self: _('New'), readonly=True, copy=False)
    project_id = fields.Many2one(
        'project.project', string='Project', required=True,
        domain=[('is_construction_project', '=', True)], tracking=True,
    )
    company_id = fields.Many2one(related='project_id.company_id', store=True, readonly=True)
    currency_id = fields.Many2one(related='project_id.construction_currency_id', readonly=True)
    date = fields.Date(default=fields.Date.context_today, required=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('provisional', 'Provisional Handover (DLP Started)'),
        ('final', 'Final Handover'),
        ('closed', 'Closed'),
    ], default='draft', required=True, copy=False, tracking=True)

    # ---------------------------------------------------------------
    # Provisional (Taking-Over) handover
    # ---------------------------------------------------------------
    provisional_handover_date = fields.Date(string='Provisional Handover Date', tracking=True)
    defects_liability_months = fields.Integer(string='Defects Liability Period (months)', default=12)
    defects_liability_end_date = fields.Date(
        string='DLP End Date', compute='_compute_dlp_end_date', store=True,
    )

    # ---------------------------------------------------------------
    # Punch / Snag list
    # ---------------------------------------------------------------
    punch_list_ids = fields.One2many('project.handover.punch.item', 'handover_id', string='Punch List')
    punch_list_open_count = fields.Integer(compute='_compute_punch_counts')
    punch_list_total_count = fields.Integer(compute='_compute_punch_counts')

    # ---------------------------------------------------------------
    # Final handover
    # ---------------------------------------------------------------
    final_handover_date = fields.Date(string='Final Handover Date', tracking=True)
    final_acceptance_notes = fields.Text(string='Final Acceptance Notes')

    # ---------------------------------------------------------------
    # Retention release (informational — actual GL entries handled by
    # Finance against the retention holdback account)
    # ---------------------------------------------------------------
    retention_held_total = fields.Monetary(
        string='Total Retention Held (Client Side)', currency_field='currency_id',
        compute='_compute_retention_held_total',
    )
    retention_release_stage1_percentage = fields.Float(
        string='Release % at Provisional Handover', default=50.0,
    )
    retention_release_stage1_amount = fields.Monetary(
        string='Stage 1 Release Amount', currency_field='currency_id', copy=False,
    )
    retention_release_stage1_done = fields.Boolean(default=False, copy=False, tracking=True)
    retention_release_stage1_date = fields.Date(copy=False)

    retention_release_stage2_percentage = fields.Float(
        string='Release % at Final Handover', default=50.0,
    )
    retention_release_stage2_amount = fields.Monetary(
        string='Stage 2 Release Amount', currency_field='currency_id', copy=False,
    )
    retention_release_stage2_done = fields.Boolean(default=False, copy=False, tracking=True)
    retention_release_stage2_date = fields.Date(copy=False)

    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('name_uniq', 'unique(name, company_id)', 'Handover reference must be unique per company!'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('project.handover') or _('New')
        return super().create(vals_list)

    @api.depends('provisional_handover_date', 'defects_liability_months')
    def _compute_dlp_end_date(self):
        for rec in self:
            if rec.provisional_handover_date and rec.defects_liability_months:
                rec.defects_liability_end_date = rec.provisional_handover_date + relativedelta(
                    months=rec.defects_liability_months)
            else:
                rec.defects_liability_end_date = False

    def _compute_punch_counts(self):
        for rec in self:
            rec.punch_list_total_count = len(rec.punch_list_ids)
            rec.punch_list_open_count = len(rec.punch_list_ids.filtered(lambda p: p.status == 'open'))

    def _compute_retention_held_total(self):
        for rec in self:
            certs = self.env['boq.payment.certificate'].search([
                ('project_id', '=', rec.project_id.id),
                ('state', '=', 'approved'),
            ])
            rec.retention_held_total = sum(certs.mapped('retention_amount'))

    # ---------------------------------------------------------------
    # Workflow
    # ---------------------------------------------------------------
    def action_confirm_provisional_handover(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Only draft handovers can be moved to provisional handover.'))
            if not rec.provisional_handover_date:
                raise UserError(_('Please set the provisional handover date first.'))
        self.write({'state': 'provisional'})

    def action_release_retention_stage1(self):
        for rec in self:
            if rec.state != 'provisional':
                raise UserError(_('Stage 1 retention release requires the handover to be at provisional stage.'))
            if rec.retention_release_stage1_done:
                raise UserError(_('Stage 1 retention has already been released.'))
            rec.write({
                'retention_release_stage1_amount': rec.retention_held_total * (
                        rec.retention_release_stage1_percentage / 100.0),
                'retention_release_stage1_done': True,
                'retention_release_stage1_date': fields.Date.context_today(rec),
            })
            rec.message_post(body=_(
                'Stage 1 retention release recorded: %.2f %s. Please coordinate the actual '
                'payment/credit note with Finance.'
            ) % (rec.retention_release_stage1_amount, rec.currency_id.symbol or ''))

    def action_final_handover(self):
        for rec in self:
            if rec.state != 'provisional':
                raise UserError(_('Final handover requires a confirmed provisional handover first.'))
            open_items = rec.punch_list_ids.filtered(lambda p: p.status == 'open')
            if open_items:
                raise UserError(_(
                    'Cannot proceed to final handover: %d punch list item(s) are still open. '
                    'Close them first or remove items that no longer apply.'
                ) % len(open_items))
            if not rec.final_handover_date:
                rec.final_handover_date = fields.Date.context_today(rec)
        self.write({'state': 'final'})

    def action_release_retention_stage2(self):
        for rec in self:
            if rec.state != 'final':
                raise UserError(_('Stage 2 retention release requires final handover to be confirmed.'))
            if rec.retention_release_stage2_done:
                raise UserError(_('Stage 2 retention has already been released.'))
            rec.write({
                'retention_release_stage2_amount': rec.retention_held_total * (
                        rec.retention_release_stage2_percentage / 100.0),
                'retention_release_stage2_done': True,
                'retention_release_stage2_date': fields.Date.context_today(rec),
            })
            rec.message_post(body=_(
                'Stage 2 (final) retention release recorded: %.2f %s. Please coordinate the actual '
                'payment/credit note with Finance.'
            ) % (rec.retention_release_stage2_amount, rec.currency_id.symbol or ''))

    def action_close(self):
        for rec in self:
            if rec.state != 'final':
                raise UserError(_('Only a project at final handover stage can be closed.'))
            if not rec.retention_release_stage2_done:
                raise UserError(_('Please release Stage 2 retention before closing the handover.'))
        self.write({'state': 'closed'})
        for rec in self:
            if not rec.project_id.actual_completion_date:
                rec.project_id.actual_completion_date = rec.final_handover_date

    def action_reset_draft(self):
        self.write({
            'state': 'draft',
            'retention_release_stage1_done': False,
            'retention_release_stage2_done': False,
        })


class ProjectHandoverPunchItem(models.Model):
    _name = 'project.handover.punch.item'
    _description = 'Handover Punch List / Snag Item'
    _order = 'status, id'

    handover_id = fields.Many2one('project.handover', required=True, ondelete='cascade', index=True)
    project_id = fields.Many2one(related='handover_id.project_id', store=True)
    description = fields.Char(string='Description', required=True)
    location = fields.Char(string='Location')
    responsible_party = fields.Selection([
        ('main_contractor', 'Main Contractor'),
        ('subcontractor', 'Subcontractor'),
        ('client_consultant', 'Client / Consultant'),
    ], string='Responsible Party', default='main_contractor', required=True)
    # subcontract_agreement_id = fields.Many2one(
    #     'subcontract.agreement', string='Related Subcontract',
    #     domain="[('project_id', '=', project_id)]",
    # )
    status = fields.Selection([
        ('open', 'Open'),
        ('closed', 'Closed'),
    ], default='open', required=True)
    date_reported = fields.Date(default=fields.Date.context_today)
    date_closed = fields.Date()

    def action_close_item(self):
        self.write({'status': 'closed', 'date_closed': fields.Date.context_today(self)})

    def action_reopen_item(self):
        self.write({'status': 'open', 'date_closed': False})