# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class WorkMeasurement(models.Model):
    """Work Measurement groups daily reports into billing periods."""
    _name = 'work.measurement'
    _description = 'Work Measurement (BOQ Execution Tracking)'
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
    period_from = fields.Date(string='Period From')
    period_to = fields.Date(string='Period To')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('linked', 'Linked to Certificate'),
    ], default='draft', required=True, copy=False, tracking=True)

    daily_report_ids = fields.Many2many(
        'site.daily.report', string='Daily Reports',
        domain="[('project_id', '=', project_id), ('state', '=', 'confirmed')]",
    )
    payment_certificate_id = fields.Many2one(
        'boq.payment.certificate', string='Payment Certificate',
        readonly=True, copy=False,
    )
    progress_ids = fields.One2many(
        'boq.line.progress', 'work_measurement_id', string='Progress Entries',
    )
    summary_line_ids = fields.One2many(
        'work.measurement.summary', 'measurement_id', string='BOQ Summary',
    )
    total_executed_value = fields.Monetary(
        string='Total Executed Value', currency_field='currency_id',
        compute='_compute_total_executed', store=True,
    )

    _sql_constraints = [
        ('name_uniq', 'unique(name, company_id)', 'WM reference must be unique per company!'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('work.measurement') or _('New')
        return super().create(vals_list)

    @api.depends('daily_report_ids', 'daily_report_ids.progress_ids')
    def _compute_total_executed(self):
        for wm in self:
            total = 0.0
            for report in wm.daily_report_ids:
                for prog in report.progress_ids:
                    total += prog.quantity_executed * prog.boq_line_id.unit_price
            wm.total_executed_value = total

    def action_confirm(self):
        for wm in self:
            if wm.state != 'draft':
                raise UserError(_('Only draft measurements can be confirmed.'))
        self.write({'state': 'confirmed'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    def action_generate_summary(self):
        """Aggregate all progress from linked daily reports into per-BOQ-line summary."""
        self.ensure_one()
        self.summary_line_ids.unlink()
        # Aggregate by BOQ line
        agg = {}
        currency = self.currency_id
        for report in self.daily_report_ids:
            for prog in report.progress_ids:
                key = prog.boq_line_id.id
                if key not in agg:
                    agg[key] = {
                        'boq_line_id': prog.boq_line_id.id,
                        'quantity_executed': 0.0,
                    }
                agg[key]['quantity_executed'] += prog.quantity_executed
        # Create summary lines
        summary_vals = []
        for data in agg.values():
            summary_vals.append((0, 0, {
                'boq_line_id': data['boq_line_id'],
                'quantity_executed': data['quantity_executed'],
            }))
        if summary_vals:
            self.write({'summary_line_ids': summary_vals})

    def action_link_to_certificate(self):
        """Link this measurement to a payment certificate (mark as linked)."""
        self.ensure_one()
        self.write({'state': 'linked'})


class WorkMeasurementSummary(models.Model):
    _name = 'work.measurement.summary'
    _description = 'Work Measurement BOQ Summary Line'

    measurement_id = fields.Many2one(
        'work.measurement', required=True, ondelete='cascade', index=True,
    )
    project_id = fields.Many2one(related='measurement_id.project_id', store=True)
    currency_id = fields.Many2one(related='measurement_id.currency_id', readonly=True)
    boq_line_id = fields.Many2one(
        'boq.line', string='BOQ Line', required=True,
        domain="[('project_id', '=', project_id), ('is_group', '=', False)]",
    )
    quantity_executed = fields.Float(string='Qty Executed', digits='Product Unit of Measure', required=True)
    unit_price = fields.Monetary(related='boq_line_id.unit_price', readonly=True)
    amount = fields.Monetary(
        string='Amount', currency_field='currency_id',
        compute='_compute_amount', store=True,
    )

    @api.depends('quantity_executed', 'unit_price')
    def _compute_amount(self):
        for line in self:
            line.amount = line.quantity_executed * line.unit_price
