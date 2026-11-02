# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class TenderTender(models.Model):
    _name = 'tender.tender'
    _description = 'Construction Tender'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'submission_deadline asc, id desc'

    # ---------------------------------------------------------------
    # Basic identification
    # ---------------------------------------------------------------
    name = fields.Char(
        string='Tender Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        tracking=True,
    )
    client_reference = fields.Char(
        string='Client Tender No.',
        help='الرقم المرجعي للمناقصة عند الجهة صاحبة المشروع',
        tracking=True,
    )
    client_id = fields.Many2one(
        'res.partner',
        string='Client',
        required=True,
        tracking=True,
    )
    description = fields.Text(string='Description')
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
    )
    user_id = fields.Many2one(
        'res.users',
        string='Responsible',
        default=lambda self: self.env.user,
        tracking=True,
    )

    # ---------------------------------------------------------------
    # Dates
    # ---------------------------------------------------------------
    submission_deadline = fields.Datetime(
        string='Submission Deadline',
        tracking=True,
    )
    opening_date = fields.Date(string='Opening Date')
    date_won = fields.Date(string='Award Date', readonly=True, copy=False)

    # ---------------------------------------------------------------
    # Financials
    # ---------------------------------------------------------------
    estimated_value = fields.Monetary(
        string='Estimated Value',
        currency_field='currency_id',
        help='القيمة التقديرية للمناقصة قبل الترسية',
    )
    awarded_value = fields.Monetary(
        string='Awarded Value',
        currency_field='currency_id',
        copy=False,
        help='القيمة الفعلية بعد الترسية، ممكن تختلف عن التقديرية',
    )

    # ---------------------------------------------------------------
    # Workflow
    # ---------------------------------------------------------------
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_evaluation', 'Under Evaluation'),
        ('won', 'Won'),
        ('lost', 'Lost'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, copy=False, tracking=True)

    lost_reason = fields.Text(string='Lost Reason', copy=False)
    cancel_reason = fields.Text(string='Cancellation Reason', copy=False)

    # ---------------------------------------------------------------
    # Project linkage (execution phase)
    # ---------------------------------------------------------------
    project_id = fields.Many2one(
        'project.project',
        string='Execution Project',
        readonly=True,
        copy=False,
        tracking=True,
    )
    project_count = fields.Integer(compute='_compute_project_count')

    boq_line_ids = fields.One2many(
        'boq.line', 'tender_id', string='BOQ Lines',
        domain=[('parent_id', '=', False)],
    )
    boq_total_contracted = fields.Monetary(
        string='BOQ Total', currency_field='currency_id',
        compute='_compute_boq_total_contracted', store=True,
    )
    boq_line_count = fields.Integer(compute='_compute_boq_line_count')

    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name, company_id)', 'Tender reference must be unique per company!'),
    ]

    # ---------------------------------------------------------------
    # CRUD
    # ---------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('tender.tender') or _('New')
        return super().create(vals_list)

    def _compute_project_count(self):
        for rec in self:
            rec.project_count = 1 if rec.project_id else 0

    @api.depends('boq_line_ids.total_contracted')
    def _compute_boq_total_contracted(self):
        for rec in self:
            rec.boq_total_contracted = sum(rec.boq_line_ids.mapped('total_contracted'))

    def _compute_boq_line_count(self):
        for rec in self:
            rec.boq_line_count = self.env['boq.line'].search_count([('tender_id', '=', rec.id)])

    # ---------------------------------------------------------------
    # State transitions
    # ---------------------------------------------------------------
    def action_submit(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Only draft tenders can be submitted.'))
            if not rec.submission_deadline:
                raise ValidationError(_('Please set a submission deadline before submitting.'))
        self.write({'state': 'submitted'})

    def action_under_evaluation(self):
        for rec in self:
            if rec.state != 'submitted':
                raise UserError(_('Only submitted tenders can move to evaluation.'))
        self.write({'state': 'under_evaluation'})

    def action_set_won(self):
        for rec in self:
            if rec.state not in ('submitted', 'under_evaluation'):
                raise UserError(_('Tender must be submitted or under evaluation before it can be won.'))
            if not rec.awarded_value:
                raise ValidationError(_('Please enter the awarded value before marking the tender as won.'))
        self.write({'state': 'won', 'date_won': fields.Date.context_today(self)})

    def action_set_lost(self):
        for rec in self:
            if rec.state not in ('submitted', 'under_evaluation'):
                raise UserError(_('Tender must be submitted or under evaluation before it can be marked as lost.'))
        self.write({'state': 'lost'})

    def action_cancel(self):
        for rec in self:
            if rec.state == 'won':
                raise UserError(_('A won tender cannot be cancelled directly. Please handle the linked project first.'))
        self.write({'state': 'cancelled'})

    def action_reset_draft(self):
        self.write({'state': 'draft', 'lost_reason': False, 'cancel_reason': False})

    # ---------------------------------------------------------------
    # Conversion to project (execution phase)
    # ---------------------------------------------------------------
    def action_create_project(self):
        self.ensure_one()
        if self.state != 'won':
            raise UserError(_('Only won tenders can be converted into an execution project.'))
        if self.project_id:
            raise UserError(_('This tender already has a linked project.'))

        project = self.env['project.project'].create({
            'name': self.name and f'{self.name} - {self.client_id.name}' or self.client_id.name,
            'partner_id': self.client_id.id,
            'company_id': self.company_id.id,
            'user_id': self.user_id.id,
            'tender_id': self.id,
            'is_construction_project': True,
            'contract_value': self.awarded_value,
            'construction_currency_id': (self.currency_id or self.company_id.currency_id).id,
        })
        self.project_id = project.id

        # Duplicate the tendered BOQ tree onto the project as the contracted baseline
        for root_line in self.boq_line_ids:
            root_line._copy_tree_to_project(project)

        return self.action_view_project()

    def action_view_project(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Execution Project'),
            'res_model': 'project.project',
            'view_mode': 'form',
            'res_id': self.project_id.id,
        }

    def action_view_boq(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Bill of Quantities'),
            'res_model': 'boq.line',
            'view_mode': 'list,form',
            'domain': [('tender_id', '=', self.id)],
            'context': {'default_tender_id': self.id},
        }