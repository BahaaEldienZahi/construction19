# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class SubcontractAgreement(models.Model):
    _name = 'subcontract.agreement'
    _description = 'Subcontract Agreement'
    _inherit = ['construction.approval.mixin', 'mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(default=lambda self: _('New'), readonly=True, copy=False)
    project_id = fields.Many2one(
        'project.project', string='Project', required=True,
        domain=[('is_construction_project', '=', True)], tracking=True,
    )
    company_id = fields.Many2one(related='project_id.company_id', store=True, readonly=True)
    currency_id = fields.Many2one(related='project_id.construction_currency_id', readonly=True)
    date = fields.Date(default=fields.Date.context_today, required=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Subcontractor', required=True, tracking=True)
    contract_value = fields.Monetary(string='Contract Value', currency_field='currency_id')
    scope_of_work = fields.Text(string='Scope of Work')
    start_date = fields.Date(string='Start Date')
    completion_date = fields.Date(string='Completion Date')
    retention_percentage = fields.Float(string='Retention %', default=5.0)

    line_ids = fields.One2many('subcontract.agreement.line', 'agreement_id', string='Lines')
    total_value = fields.Monetary(
        string='Total Value', currency_field='currency_id',
        compute='_compute_total_value', store=True,
    )

    _sql_constraints = [
        ('name_uniq', 'unique(name, company_id)', 'Agreement reference must be unique per company!'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('subcontract.agreement') or _('New')
        return super().create(vals_list)

    @api.depends('line_ids.subtotal')
    def _compute_total_value(self):
        for ag in self:
            ag.total_value = sum(ag.line_ids.mapped('subtotal'))


class SubcontractAgreementLine(models.Model):
    _name = 'subcontract.agreement.line'
    _description = 'Subcontract Agreement Line'

    agreement_id = fields.Many2one(
        'subcontract.agreement', required=True, ondelete='cascade', index=True,
    )
    project_id = fields.Many2one(related='agreement_id.project_id', store=True)
    currency_id = fields.Many2one(related='agreement_id.currency_id', readonly=True)

    boq_line_id = fields.Many2one(
        'boq.line', string='BOQ Line', required=True,
        domain="[('project_id', '=', project_id), ('is_group', '=', False)]",
    )
    name = fields.Char(related='boq_line_id.name', string='Description', readonly=True)
    code = fields.Char(related='boq_line_id.code', readonly=True)
    uom_id = fields.Many2one(related='boq_line_id.uom_id', readonly=True)

    executed_qty = fields.Float(
        string='Executed Qty', digits='Product Unit of Measure',
        compute='_compute_execution_stats', store=True,
        help='Sum of quantities from approved subcontractor payment certificates',
    )
    remaining_qty = fields.Float(
        string='Remaining Qty', digits='Product Unit of Measure',
        compute='_compute_execution_stats', store=True,
    )
    execution_percentage = fields.Float(
        string='Execution %', compute='_compute_execution_stats', store=True,
    )
    executed_amount = fields.Monetary(
        string='Executed Amount', currency_field='currency_id',
        compute='_compute_execution_stats', store=True,
    )

    @api.depends('agreement_id.state', 'agreement_id.line_ids.executed_qty')
    def _compute_execution_stats(self):
        for line in self:
            cert_lines = self.env['subcontract.payment.certificate.line'].search([
                ('boq_line_id', '=', line.boq_line_id.id),
                ('certificate_id.subcontract_agreement_id', '=', line.agreement_id.id),
                ('certificate_id.state', '=', 'approved'),
            ])
            line.executed_qty = sum(cert_lines.mapped('quantity_this_period'))
            line.executed_amount = sum(cert_lines.mapped('amount_this_period'))
            line.remaining_qty = line.quantity - line.executed_qty
            line.execution_percentage = (
                (line.executed_qty / line.quantity * 100) if line.quantity else 0.0
            )

    quantity = fields.Float(string='Quantity', digits='Product Unit of Measure', required=True, default=1.0)
    unit_price = fields.Monetary(string='Unit Price', currency_field='currency_id')
    subtotal = fields.Monetary(
        string='Subtotal', currency_field='currency_id',
        compute='_compute_subtotal', store=True,
    )

    @api.depends('quantity', 'unit_price')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.unit_price

    @api.onchange('boq_line_id')
    def _onchange_boq_line_id(self):
        if self.boq_line_id:
            self.name = self.boq_line_id.name
            self.code = self.boq_line_id.code
            self.uom_id = self.boq_line_id.uom_id
            self.unit_price = self.boq_line_id.unit_price

    @api.constrains('boq_line_id', 'agreement_id')
    def _check_boq_line_project_match(self):
        for line in self:
            if line.boq_line_id and line.boq_line_id.project_id != line.agreement_id.project_id:
                raise ValidationError(_('The BOQ line does not belong to the same project as the agreement.'))
