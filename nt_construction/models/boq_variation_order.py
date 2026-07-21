# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class BoqVariationOrder(models.Model):
    _name = 'boq.variation.order'
    _description = 'BOQ Variation Order'
    _inherit = ['construction.approval.mixin', 'mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(default=lambda self: _('New'), readonly=True, copy=False)
    project_id = fields.Many2one(
        'project.project', string='Project', required=True,
        domain=[('is_construction_project', '=', True)], tracking=True,
    )
    date = fields.Date(default=fields.Date.context_today, required=True)
    reason = fields.Text(string='Reason / Justification')
    currency_id = fields.Many2one(related='project_id.construction_currency_id', readonly=True)

    line_ids = fields.One2many('boq.variation.order.line', 'variation_order_id', string='Lines')
    total_delta_amount = fields.Monetary(
        string='Net Change', currency_field='currency_id',
        compute='_compute_total_delta_amount', store=True,
    )
    applied = fields.Boolean(readonly=True, copy=False, default=False)
    # Note: this model overrides the mixin's state field to add clearer labels
    # and a rejection option. All mixin state transitions (including reject)
    # are inherited from construction.approval.mixin.
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('submitted', 'Pending Approval'),
            ('approved_l1', 'Level 1 Approved'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('cancelled', 'Cancelled'),
        ],
        string='Status',
        default='draft',
        tracking=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('boq.variation.order') or _('New')
        return super().create(vals_list)

    @api.depends('line_ids.delta_amount')
    def _compute_total_delta_amount(self):
        for vo in self:
            vo.total_delta_amount = sum(vo.line_ids.mapped('delta_amount'))

    def _on_final_approval(self):
        for vo in self:
            if vo.applied:
                continue
            for line in vo.line_ids:
                line._apply_to_boq()
            vo.project_id.contract_value += vo.total_delta_amount
            vo.applied = True


class BoqVariationOrderLine(models.Model):
    _name = 'boq.variation.order.line'
    _description = 'BOQ Variation Order Line'

    variation_order_id = fields.Many2one(
        'boq.variation.order', required=True, ondelete='cascade', index=True,
    )
    project_id = fields.Many2one(related='variation_order_id.project_id', store=True)
    currency_id = fields.Many2one(related='variation_order_id.currency_id', readonly=True)

    boq_line_id = fields.Many2one(
        'boq.line', string='Existing BOQ Line',
        help='اجال بوال موالد وو التعبي و فمةة بال جالي. سيبه فارق دو البال اطم المحبال.',
    )
    parent_boq_line_id = fields.Many2one(
        'boq.line', string='Parent (for new items)',
        help='ل، البال اطم الححبال الجناتل ارمار, اجالد بدت اك حالد حهةرال.',
    )
    code = fields.Char(string='Item Code')
    name = fields.Char(string='Description', required=True)
    uom_id = fields.Many2one('uom.uom', string='UoM')
    delta_qty = fields.Float(string='Qty Change (+/-)', digits='Product Unit of Measure')
    unit_price = fields.Monetary(string='Unit Price', currency_field='currency_id')
    delta_amount = fields.Monetary(
        string='Amount Change', currency_field='currency_id',
        compute='_compute_delta_amount', store=True,
    )

    @api.depends('delta_qty', 'unit_price')
    def _compute_delta_amount(self):
        for line in self:
            line.delta_amount = line.delta_qty * line.unit_price

    @api.onchange('boq_line_id')
    def _onchange_boq_line_id(self):
        if self.boq_line_id:
            self.name = self.boq_line_id.name
            self.code = self.boq_line_id.code
            self.uom_id = self.boq_line_id.uom_id
            self.unit_price = self.boq_line_id.unit_price

    @api.constrains('boq_line_id', 'parent_boq_line_id', 'variation_order_id')
    def _check_boq_line_project_match(self):
        for line in self:
            project = line.variation_order_id.project_id
            if line.boq_line_id and line.boq_line_id.project_id != project:
                raise ValidationError(_('البوال الجماجال مع ثارف اللاد السيود ✆ر عمرb�e6��.ام.'))
            if line.parent_boq_line_id and line.parent_boq_line_id.project_id != project:
                raise ValidationError(_('البوال الاسة الجماجال م�5 تارر السيود ✆ر عمر السيود '))

    def _apply_to_boq(self):
        self.ensure_one()
        if self.boq_line_id:
            vals = {'quantity_contracted': self.boq_line_id.quantity_contracted + self.delta_qty}
            if self.unit_price:
                vals['unit_price'] = self.unit_price
            self.boq_line_id.write(vals)
        else:
            self.env['boq.line'].create({
                'project_id': self.project_id.id,
                'parent_id': self.parent_boq_line_id.id if self.parent_boq_line_id else False,
                'code': self.code,
                'name': self.name,
                'uom_id': self.uom_id.id,
                'quantity_contracted': self.delta_qty,
                'unit_price': self.unit_price,
            })
