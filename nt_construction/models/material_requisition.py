# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class MaterialRequisition(models.Model):
    """طلب صرف مواد للموقع — Material Requisition from Site"""
    _name = 'material.requisition'
    _description = 'Material Requisition (Site Request)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(default=lambda self: _('New'), readonly=True, copy=False)
    project_id = fields.Many2one(
        'project.project', string='Project', required=True,
        domain=[('is_construction_project', '=', True)], tracking=True,
    )
    company_id = fields.Many2one(related='project_id.company_id', store=True, readonly=True)
    date = fields.Date(default=fields.Date.context_today, required=True, tracking=True)
    requested_by = fields.Many2one('res.users', string='Requested By', default=lambda self: self.env.user)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('partially_delivered', 'Partially Delivered'),
        ('fully_delivered', 'Fully Delivered'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', required=True, copy=False, tracking=True)
    rejection_reason = fields.Text(copy=False)

    line_ids = fields.One2many('material.requisition.line', 'requisition_id', string='Material Lines')
    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('name_uniq', 'unique(name, company_id)', 'Requisition reference must be unique per company!'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('material.requisition') or _('New')
        return super().create(vals_list)

    def action_submit(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Only draft requisitions can be submitted.'))
            if not rec.line_ids:
                raise UserError(_('Please add at least one material line before submitting.'))
        self.write({'state': 'submitted'})

    def action_approve(self):
        for rec in self:
            if rec.state != 'submitted':
                raise UserError(_('Only submitted requisitions can be approved.'))
        self.write({'state': 'approved'})

    def action_reject(self):
        self.write({'state': 'rejected'})

    def action_reset_draft(self):
        self.write({'state': 'draft', 'rejection_reason': False})


class MaterialRequisitionLine(models.Model):
    _name = 'material.requisition.line'
    _description = 'Material Requisition Line'

    requisition_id = fields.Many2one('material.requisition', required=True, ondelete='cascade', index=True)
    project_id = fields.Many2one(related='requisition_id.project_id', store=True)
    boq_line_id = fields.Many2one(
        'boq.line', string='BOQ Line',
        domain="[('project_id', '=', project_id), ('is_group', '=', False)]",
        help='اربط البند ببند BOQ للتتبع',
    )
    product_id = fields.Many2one('product.product', string='Material/Product')
    description = fields.Char(string='Description', required=True)
    uom_id = fields.Many2one('uom.uom', string='UoM')
    quantity_requested = fields.Float(string='Qty Requested', digits='Product Unit of Measure', required=True, default=1.0)
    quantity_delivered = fields.Float(string='Qty Delivered', digits='Product Unit of Measure', readonly=True, default=0.0)
    quantity_remaining = fields.Float(string='Qty Remaining', compute='_compute_remaining', store=True, digits='Product Unit of Measure')
    delivery_status = fields.Selection([
        ('pending', 'Pending'),
        ('partial', 'Partial'),
        ('complete', 'Complete'),
    ], string='Delivery', compute='_compute_delivery_status', store=True)
    po_line_id = fields.Many2one('purchase.order.line', string='PO Line', readonly=True)

    @api.depends('quantity_requested', 'quantity_delivered')
    def _compute_remaining(self):
        for line in self:
            line.quantity_remaining = line.quantity_requested - line.quantity_delivered

    @api.depends('quantity_requested', 'quantity_delivered')
    def _compute_delivery_status(self):
        for line in self:
            if line.quantity_delivered >= line.quantity_requested:
                line.delivery_status = 'complete'
            elif line.quantity_delivered > 0:
                line.delivery_status = 'partial'
            else:
                line.delivery_status = 'pending'
