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

    picking_id = fields.Many2one(
        'stock.picking', string='Inventory Transfer', readonly=True, copy=False,
        help='حركة المخزون اللي اتعملت تلقائي لما الطلب اتاعتمد',
    )
    picking_state = fields.Selection(related='picking_id.state', string='Transfer Status', readonly=True)

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
        for rec in self:
            if not rec.picking_id:
                rec._create_stock_picking()

    def action_reject(self):
        self.write({'state': 'rejected'})

    def action_reset_draft(self):
        self.write({'state': 'draft', 'rejection_reason': False})

    def action_view_picking(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Inventory Transfer'),
            'res_model': 'stock.picking',
            'view_mode': 'form',
            'res_id': self.picking_id.id,
        }

    # ---------------------------------------------------------------
    # Inventory (Stock) integration
    # ---------------------------------------------------------------
    def _create_stock_picking(self):
        """Create a real Odoo Inventory internal transfer moving the
        requested products from the company warehouse to this project's
        site stock location, so the request is immediately visible and
        actionable in the Inventory app (Transfers)."""
        self.ensure_one()
        stock_lines = self.line_ids.filtered('product_id')
        if not stock_lines:
            # Nothing trackable in stock (pure text/description lines only)
            return False

        warehouse = self.env['stock.warehouse'].search(
            [('company_id', '=', self.company_id.id or self.env.company.id)], limit=1)
        picking_type = warehouse.int_type_id if warehouse else False
        if not picking_type:
            # Defensive fallback in case int_type_id isn't set for some reason
            picking_type = self.env['stock.picking.type'].sudo().search([
                ('code', '=', 'internal'),
                ('company_id', '=', self.company_id.id or self.env.company.id),
            ], limit=1)
        if not picking_type:
            raise UserError(_(
                'No warehouse with an Internal Transfers operation type was found '
                'for this company. Please configure a warehouse in Inventory first.'
            ))
        project_location = self.project_id.sudo()._get_or_create_stock_location()

        source_location = picking_type.default_location_src_id or (warehouse.lot_stock_id if warehouse else False)
        picking = self.env['stock.picking'].sudo().create({
            'picking_type_id': picking_type.id,
            'location_id': source_location.id,
            'location_dest_id': project_location.id,
            'origin': self.name,
            'company_id': self.company_id.id or self.env.company.id,
        })
        for line in stock_lines:
            move = self.env['stock.move'].sudo().create({
                'description_picking': line.product_id.display_name or line.description,
                'picking_id': picking.id,
                'product_id': line.product_id.id,
                'product_uom_qty': line.quantity_requested,
                'product_uom': (line.uom_id or line.product_id.uom_id).id,
                'location_id': picking.location_id.id,
                'location_dest_id': picking.location_dest_id.id,
                'company_id': picking.company_id.id,
            })
            line.move_id = move.id

        picking.action_confirm()
        try:
            picking.action_assign()
        except Exception:
            # Reservation can legitimately fail on insufficient stock;
            # the transfer still exists and is visible/actionable in
            # the Inventory app either way.
            pass

        self.picking_id = picking.id
        return picking

    @staticmethod
    def _get_move_done_qty(move):
        """Best-effort, version-safe read of the actually-delivered
        quantity of a stock.move, since the underlying field name has
        changed across Odoo versions (quantity_done -> quantity/picked)."""
        if not move or move.state == 'cancel':
            return 0.0
        if move.state != 'done':
            return 0.0
        if 'quantity' in move._fields:
            try:
                return move.quantity
            except Exception:
                pass
        if 'quantity_done' in move._fields:
            return move.quantity_done
        move_lines = move.move_line_ids
        if move_lines and 'qty_done' in move_lines._fields:
            return sum(move_lines.mapped('qty_done'))
        if move_lines and 'quantity' in move_lines._fields:
            return sum(move_lines.mapped('quantity'))
        return move.product_uom_qty if move.state == 'done' else 0.0

    def action_sync_delivered_quantities(self):
        """Pull actually-delivered quantities from the linked Inventory
        transfer(s) back onto the requisition lines. Safe to call
        repeatedly (e.g. from a scheduled action or manually)."""
        for rec in self:
            lines_with_move = rec.line_ids.filtered('move_id')
            if not lines_with_move:
                continue
            for line in lines_with_move:
                line.quantity_delivered = rec._get_move_done_qty(line.move_id)
            if rec.picking_id.state == 'done' and rec.state in ('approved', 'partially_delivered'):
                if all(l.delivery_status == 'complete' for l in rec.line_ids.filtered('product_id')):
                    rec.state = 'fully_delivered'
                elif any(l.quantity_delivered for l in rec.line_ids):
                    rec.state = 'partially_delivered'

    @api.model
    def _cron_sync_delivered_quantities(self):
        open_recs = self.search([
            ('state', 'in', ('approved', 'partially_delivered')),
            ('picking_id', '!=', False),
        ])
        if open_recs:
            open_recs.action_sync_delivered_quantities()


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
    move_id = fields.Many2one('stock.move', string='Stock Move', readonly=True, copy=False)
    state = fields.Selection(
        related='requisition_id.state',
        string='Status',
        store=True,
        readonly=True,
    )

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
