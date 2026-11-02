from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError


class ProjectHandover(models.Model):
    """التسليم الابتدائي والنهائي للمشروع: يتابع تاريخ التسليم الابتدائي،
    فترة الصيانة (Defects Liability Period)، قائمة الملاحظات (Punch/Snag List)،
    والإفراج التدريجي عن الضمان لحد التسليم النهائي وإغلاق المشروع."""

    _name = 'project.handover'
    _description = 'Project Handover / Delivery Certificate'
    _check_company_auto = True
    _inherit = ['construction.workflow.guard', 'mail.thread', 'mail.activity.mixin']
    _workflow_guarded_fields = (
        'state',
        'retention_release_stage1_amount', 'retention_release_stage1_done', 'retention_release_stage1_date',
        'retention_release_stage2_amount', 'retention_release_stage2_done', 'retention_release_stage2_date',
    )
    _order = 'date desc, id desc'

    name = fields.Char(default=lambda self: self.env._('New'), readonly=True, copy=False)
    project_id = fields.Many2one(
        'project.project', required=True,
        domain=[('is_construction_project', '=', True)], tracking=True,
        check_company=True,
    )
    company_id = fields.Many2one(related='project_id.company_id', store=True, readonly=True)
    currency_id = fields.Many2one(related='project_id.construction_currency_id', readonly=True)
    date = fields.Date(default=fields.Date.context_today, required=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('provisional', 'Provisional (DLP)'),
        ('final', 'Final Handover'),
        ('closed', 'Closed'),
    ], default='draft', required=True, copy=False, tracking=True)

    # ---------------------------------------------------------------
    # Provisional (Taking-Over) handover
    # ---------------------------------------------------------------
    provisional_handover_date = fields.Date(tracking=True)
    defects_liability_months = fields.Integer(string='Defects Liability Period (months)', default=12)
    defects_liability_end_date = fields.Date(
        string='DLP End Date', compute='_compute_dlp_end_date', store=True,
    )

    # ---------------------------------------------------------------
    # Punch / Snag list
    # ---------------------------------------------------------------
    punch_list_ids = fields.One2many('project.handover.punch.item', 'handover_id')
    punch_list_open_count = fields.Integer(compute='_compute_punch_counts')
    punch_list_total_count = fields.Integer(compute='_compute_punch_counts')

    # ---------------------------------------------------------------
    # Final handover
    # ---------------------------------------------------------------
    final_handover_date = fields.Date(tracking=True)
    final_acceptance_notes = fields.Text()

    # ---------------------------------------------------------------
    # Retention release (informational — actual GL entries handled by
    # Finance against the retention holdback account)
    # ---------------------------------------------------------------
    retention_held_total = fields.Monetary(
        string='Total Retention Held (Client Side)', currency_field='currency_id',
        compute='_compute_retention_held_total',
        groups='nt_construction.group_construction_see_amounts,project.group_project_manager',
    )
    retention_release_stage1_percentage = fields.Float(
        string='Release % at Provisional Handover', default=50.0,
    )
    retention_release_stage1_amount = fields.Monetary(
        string='Stage 1 Release Amount', currency_field='currency_id', copy=False,
        groups='nt_construction.group_construction_see_amounts,project.group_project_manager',
    )
    retention_release_stage1_done = fields.Boolean(default=False, copy=False, tracking=True)
    retention_release_stage1_date = fields.Date(copy=False)

    retention_release_stage2_percentage = fields.Float(
        string='Release % at Final Handover', default=50.0,
    )
    retention_release_stage2_amount = fields.Monetary(
        string='Stage 2 Release Amount', currency_field='currency_id', copy=False,
        groups='nt_construction.group_construction_see_amounts,project.group_project_manager',
    )
    retention_release_stage2_done = fields.Boolean(default=False, copy=False, tracking=True)
    retention_release_stage2_date = fields.Date(copy=False)

    notes = fields.Text()

    _name_uniq = models.Constraint(
        'unique(name, company_id)',
        'Handover reference must be unique per company!',
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', self.env._('New')) == self.env._('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('project.handover') or self.env._('New')
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
    def action_view_project(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'project.project',
            'view_mode': 'form',
            'res_id': self.project_id.id,
        }

    def action_view_open_punch_items(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('Open Punch Items'),
            'res_model': 'project.handover.punch.item',
            'view_mode': 'list',
            'domain': [('handover_id', '=', self.id), ('status', '=', 'open')],
            'context': {'default_handover_id': self.id},
        }

    def action_confirm_provisional_handover(self):
        self._check_construction_role('nt_construction.group_construction_project_manager')
        for rec in self:
            if rec.state != 'draft':
                raise UserError(self.env._('Only draft handovers can be moved to provisional handover.'))
            if not rec.provisional_handover_date:
                raise UserError(self.env._('Please set the provisional handover date first.'))
        self._workflow_write({'state': 'provisional'})

    def action_release_retention_stage1(self):
        self._check_construction_role('nt_construction.group_construction_accountant')
        for rec in self:
            if rec.state != 'provisional':
                raise UserError(self.env._('Stage 1 retention release requires the handover to be at provisional stage.'))
            if rec.retention_release_stage1_done:
                raise UserError(self.env._('Stage 1 retention has already been released.'))
            rec._workflow_write({
                'retention_release_stage1_amount': rec.retention_held_total * (
                        rec.retention_release_stage1_percentage / 100.0),
                'retention_release_stage1_done': True,
                'retention_release_stage1_date': fields.Date.context_today(rec),
            })
            rec.message_post(body=self.env._(
                'Stage 1 retention release recorded: %(amount).2f %(currency)s. Please coordinate the actual '
                'payment/credit note with Finance.',
                amount=rec.retention_release_stage1_amount, currency=rec.currency_id.symbol or '',
            ))

    def action_final_handover(self):
        self._check_construction_role('nt_construction.group_construction_project_manager')
        for rec in self:
            if rec.state != 'provisional':
                raise UserError(self.env._('Final handover requires a confirmed provisional handover first.'))
            open_items = rec.punch_list_ids.filtered(lambda p: p.status == 'open')
            if open_items:
                raise UserError(self.env._(
                    'Cannot proceed to final handover: %s punch list item(s) are still open. '
                    'Close them first or remove items that no longer apply.',
                    len(open_items),
                ))
            if not rec.final_handover_date:
                rec.final_handover_date = fields.Date.context_today(rec)
        self._workflow_write({'state': 'final'})

    def action_release_retention_stage2(self):
        self._check_construction_role('nt_construction.group_construction_accountant')
        for rec in self:
            if rec.state != 'final':
                raise UserError(self.env._('Stage 2 retention release requires final handover to be confirmed.'))
            if rec.retention_release_stage2_done:
                raise UserError(self.env._('Stage 2 retention has already been released.'))
            rec._workflow_write({
                'retention_release_stage2_amount': rec.retention_held_total * (
                        rec.retention_release_stage2_percentage / 100.0),
                'retention_release_stage2_done': True,
                'retention_release_stage2_date': fields.Date.context_today(rec),
            })
            rec.message_post(body=self.env._(
                'Stage 2 (final) retention release recorded: %(amount).2f %(currency)s. Please coordinate the actual '
                'payment/credit note with Finance.',
                amount=rec.retention_release_stage2_amount, currency=rec.currency_id.symbol or '',
            ))

    def action_close(self):
        self._check_construction_role('nt_construction.group_construction_project_manager')
        for rec in self:
            if rec.state != 'final':
                raise UserError(self.env._('Only a project at final handover stage can be closed.'))
            if not rec.retention_release_stage2_done:
                raise UserError(self.env._('Please release Stage 2 retention before closing the handover.'))
        self._workflow_write({'state': 'closed'})
        for rec in self:
            if not rec.project_id.actual_completion_date:
                rec.project_id.actual_completion_date = rec.final_handover_date

    def action_reset_draft(self):
        self._check_construction_role('nt_construction.group_construction_project_manager')
        if any(rec.retention_release_stage1_done or rec.retention_release_stage2_done for rec in self):
            # DECISIONS Q6: once retention is released the handover cannot be reopened
            raise UserError(self.env._('A handover with a recorded retention release cannot be reset to draft.'))
        self._workflow_write({
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
    description = fields.Char(required=True)
    location = fields.Char()
    responsible_party = fields.Selection([
        ('main_contractor', 'Main Contractor'),
        ('subcontractor', 'Subcontractor'),
        ('client_consultant', 'Client / Consultant'),
    ], default='main_contractor', required=True)
    subcontract_agreement_id = fields.Many2one(
        'subcontract.agreement', string='Related Subcontract',
        domain="[('project_id', '=', project_id)]",
    )
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
