# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class CashflowForecast(models.Model):
    _name = 'construction.cashflow.forecast'
    _description = 'Cash Flow Forecast'
    _order = 'projected_date asc, id desc'

    name = fields.Char(default=lambda self: _('New'), readonly=True, copy=False)
    project_id = fields.Many2one(
        'project.project', string='Project', required=True,
        domain=[('is_construction_project', '=', True)], tracking=True,
    )
    currency_id = fields.Many2one(related='project_id.construction_currency_id', readonly=True)

    projected_date = fields.Date(string='Projected Date', required=True)
    projected_amount = fields.Monetary(string='Projected Amount', currency_field='currency_id')
    actual_receipt_date = fields.Date(string='Actual Receipt Date', copy=False)
    actual_amount = fields.Monetary(string='Actual Amount', currency_field='currency_id')

    source_certificate_id = fields.Many2one(
        'boq.payment.certificate', string='Source Certificate',
        domain="["project_id', '=', project_id)]",
    )

    status = fields.Selection([
        ('planned', 'Planned'),
        ('invoiced', 'Invoiced'),
        ('received', 'Received'),
        ('overdue', 'Overdue'),
    ], string='Status', default='planned', compute='_compute_status', store=True)

    variance = fields.Monetary(
        string='Variance', currency_field='currency_id',
        compute='_compute_variance', store=True,
    )

    notes = fields.Text(string='Notes')

    @api.depends('projected_amount', 'actual_amount')
    def _compute_variance(self):
        for rec in self:
            rec.variance = rec.actual_amount - rec.projected_amount

    @api.depends('projected_date', 'source_certificate_id.state', 'actual_amount')
    def _compute_status(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.actual_amount:
                rec.status = 'received'
            elif rec.source_certificate_id and rec.source_certificate_id.state == 'approved':
                rec.status = 'invoiced'
            elif rec.projected_date and rec.projected_date < today:
                rec.status = 'overdue'
            else:
                rec.status = 'planned'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'construction.cashflow.forecast') or _('New')
        return super().create(vals_list)
