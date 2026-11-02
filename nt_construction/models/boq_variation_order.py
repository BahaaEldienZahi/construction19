from odoo import api, fields, models
from odoo.exceptions import ValidationError


class BoqVariationOrder(models.Model):
    _name = 'boq.variation.order'
    _description = 'BOQ Variation Order'
    _check_company_auto = True
    _inherit = ['construction.approval.mixin', 'mail.thread', 'mail.activity.mixin']

    _workflow_guarded_fields = (
        'state', 'approver_l1_id', 'approval_l1_date', 'approver_l2_id', 'approval_l2_date', 'applied',
    )
    _submit_group_xmlids = (
        'nt_construction.group_construction_quantity_surveyor',
        'nt_construction.group_construction_project_manager',
    )
    _order = 'date desc, id desc'

    name = fields.Char(default=lambda self: self.env._('New'), readonly=True, copy=False)
    project_id = fields.Many2one(
        'project.project', required=True,
        domain=[('is_construction_project', '=', True)], tracking=True,
        check_company=True,
    )
    date = fields.Date(default=fields.Date.context_today, required=True)
    reason = fields.Text(string='Reason / Justification')
    company_id = fields.Many2one(related='project_id.company_id', store=True, index=True)
    currency_id = fields.Many2one(related='project_id.construction_currency_id', readonly=True)

    line_ids = fields.One2many('boq.variation.order.line', 'variation_order_id', string='Lines')
    total_delta_amount = fields.Monetary(
        string='Net Change', currency_field='currency_id',
        compute='_compute_total_delta_amount', store=True,
        groups='nt_construction.group_construction_see_amounts,project.group_project_manager',
    )
    applied = fields.Boolean(readonly=True, copy=False, default=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', self.env._('New')) == self.env._('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('boq.variation.order') or self.env._('New')
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
    _inherit = ['construction.locked.line']
    _locked_parent_field = 'variation_order_id'
    _description = 'BOQ Variation Order Line'

    variation_order_id = fields.Many2one(
        'boq.variation.order', required=True, ondelete='cascade', index=True,
    )
    project_id = fields.Many2one(related='variation_order_id.project_id', store=True)
    currency_id = fields.Many2one(related='variation_order_id.currency_id', readonly=True)

    boq_line_id = fields.Many2one(
        'boq.line', string='Existing BOQ Line',
        help='اختار بند موجود لو التغيير في كمية بند حالي. سيبه فاضي لو البند ده جديد.',
    )
    parent_boq_line_id = fields.Many2one(
        'boq.line', string='Parent (for new items)',
        help='لو البند ده جديد بالكامل، اختار تحت أي Chapter هيتضاف.',
    )
    code = fields.Char(string='Item Code')
    name = fields.Char(string='Description', required=True)
    uom_id = fields.Many2one('uom.uom', string='UoM')
    delta_qty = fields.Float(string='Qty Change (+/-)', digits='Product Unit of Measure')
    unit_price = fields.Monetary(currency_field='currency_id', groups='nt_construction.group_construction_see_amounts,project.group_project_manager')
    delta_amount = fields.Monetary(
        string='Amount Change', currency_field='currency_id',
        compute='_compute_delta_amount', store=True,
        groups='nt_construction.group_construction_see_amounts,project.group_project_manager',
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
                raise ValidationError(self.env._('The selected BOQ line does not belong to the variation order\'s project.'))
            if line.parent_boq_line_id and line.parent_boq_line_id.project_id != project:
                raise ValidationError(self.env._('The selected parent line does not belong to the variation order\'s project.'))

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
