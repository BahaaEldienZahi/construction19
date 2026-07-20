# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare


class BoqLine(models.Model):
    _name = 'boq.line'
    _description = 'BOQ Line (Bill of Quantities)'
    _parent_name = 'parent_id'
    _parent_store = True
    _order = 'parent_path, sequence, id'
    _rec_name = 'name'

    # ---------------------------------------------------------------
    # Ownership: a BOQ line belongs to a Tender (as-bid) OR a Project
    # (as-contracted / as-built). Never both.
    # ---------------------------------------------------------------
    tender_id = fields.Many2one(
        'tender.tender', string='Tender',
        ondelete='cascade', index=True,
    )
    project_id = fields.Many2one(
        'project.project', string='Project',
        ondelete='cascade', index=True,
    )
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        related='company_id.currency_id', string='Currency', readonly=True,
    )

    # ---------------------------------------------------------------
    # Hierarchy: Chapter -> Item -> Sub-item
    # ---------------------------------------------------------------
    parent_id = fields.Many2one(
        'boq.line', string='Parent Line',
        ondelete='cascade', index=True,
    )
    child_ids = fields.One2many('boq.line', 'parent_id', string='Sub Lines')
    parent_path = fields.Char(index=True, unaccent=False)
    level = fields.Integer(compute='_compute_level', store=True)
    is_group = fields.Boolean(compute='_compute_is_group', store=True,
                              help='True لو البند ده Chapter/فصل بيحتوي بنود فرعية')

    sequence = fields.Integer(default=10)
    code = fields.Char(string='Item Code', help='رقم البند حسب جدول الكميات (مثال: 1.2.3)')
    name = fields.Char(string='Description', required=True)

    # ---------------------------------------------------------------
    # Quantities & pricing (leaf lines only — group lines roll up)
    # ---------------------------------------------------------------
    uom_id = fields.Many2one('uom.uom', string='UoM')
    quantity_contracted = fields.Float(string='Contracted Qty', digits='Product Unit of Measure')
    unit_price = fields.Monetary(string='Unit Price', currency_field='currency_id')

    total_contracted = fields.Monetary(
        string='Total Contracted', currency_field='currency_id',
        compute='_compute_total_contracted', store=True, recursive=True,
    )

    # ---------------------------------------------------------------
    # Execution progress (rolled up from boq.line.progress records)
    # ---------------------------------------------------------------
    progress_ids = fields.One2many('boq.line.progress', 'boq_line_id', string='Progress Entries')
    quantity_executed_cumulative = fields.Float(
        string='Executed Qty (Cumulative)',
        compute='_compute_execution', store=True, digits='Product Unit of Measure',
        recursive=True,
    )
    amount_executed_cumulative = fields.Monetary(
        string='Executed Value (Cumulative)', currency_field='currency_id',
        compute='_compute_execution', store=True, recursive=True,
    )
    percentage_complete = fields.Float(
        string='% Complete', compute='_compute_execution', store=True, recursive=True,
    )

    # ---------------------------------------------------------------
    # Optional linkage to execution tracking
    # ---------------------------------------------------------------
    analytic_account_id = fields.Many2one(
        'account.analytic.account', string='Analytic Account',
        help='لتتبع التكلفة الفعلية (مواد/عمالة/مقاولين باطن) المرتبطة بالبند ده',
    )
    task_id = fields.Many2one('project.task', string='Related Task')

    # ---------------------------------------------------------------
    # Cost control: committed cost from subcontractor / material POs
    # ---------------------------------------------------------------
    po_line_ids = fields.One2many('purchase.order.line', 'boq_line_id', string='Purchase Order Lines')
    subcontract_line_ids = fields.One2many(
        'subcontract.agreement.line', 'boq_line_id', string='Subcontract Agreement Lines',
    )
    committed_amount = fields.Monetary(
        string='Committed Cost', currency_field='currency_id',
        compute='_compute_committed_amount', store=True,
        help='إجمالي قيمة أوامر الشراء (خامات/معدات) المؤكدة + اتفاقيات المقاولة من الباطن المعتمدة والمرتبطة بالبند ده',
    )
    actual_cost = fields.Monetary(
        string='Actual Cost', currency_field='currency_id',
        compute='_compute_actual_cost', store=True,
        help='التكلفة الفعلية من الفواتير المستلمة (vendor bills) المرتبطة بأوامر الشراء للمشروع',
    )
    cost_variance = fields.Monetary(
        string='Cost Variance', currency_field='currency_id',
        compute='_compute_cost_variance', store=True,
        help='الفرق بين المتعاقد عليه والفعلي: قيمة البند - التكلفة الفعلية',
    )

    @api.depends(
        'po_line_ids.price_subtotal', 'po_line_ids.order_id.state',
        'subcontract_line_ids.subtotal', 'subcontract_line_ids.agreement_id.state',
    )
    def _compute_committed_amount(self):
        for line in self:
            confirmed_po = line.po_line_ids.filtered(lambda l: l.order_id.state in ('purchase', 'done'))
            confirmed_sub = line.subcontract_line_ids.filtered(lambda l: l.agreement_id.state == 'approved')
            line.committed_amount = sum(confirmed_po.mapped('price_subtotal')) + sum(
                confirmed_sub.mapped('subtotal'))

    @api.depends(
        'po_line_ids.order_id.invoice_line_ids.price_subtotal',
        'po_line_ids.order_id.invoice_ids.move_type',
        'po_line_ids.order_id.invoice_ids.state',
    )
    def _compute_actual_cost(self):
        for line in self:
            total = 0.0
            for po_line in line.po_line_ids:
                order = po_line.order_id
                for inv in order.invoice_ids.filtered(
                    lambda i: i.move_type == 'in_invoice' and i.state == 'posted'
                ):
                    for inv_line in inv.invoice_line_ids:
                        if inv_line.purchase_line_id == po_line:
                            total += inv_line.price_subtotal
            line.actual_cost = total

    @api.depends('amount_executed_cumulative', 'actual_cost')
    def _compute_cost_variance(self):
        for line in self:
            line.cost_variance = line.amount_executed_cumulative - line.actual_cost

    # ---------------------------------------------------------------
    # Compute methods
    # ---------------------------------------------------------------
    @api.depends('parent_path')
    def _compute_level(self):
        for line in self:
            line.level = line.parent_path.count('/') - 1 if line.parent_path else 0

    @api.depends('child_ids')
    def _compute_is_group(self):
        for line in self:
            line.is_group = bool(line.child_ids)

    @api.depends('quantity_contracted', 'unit_price', 'child_ids.total_contracted')
    def _compute_total_contracted(self):
        # bottom-up: group lines sum their children, leaf lines compute qty * price
        for line in self.sorted(key=lambda l: l.level, reverse=True):
            if line.child_ids:
                line.total_contracted = sum(line.child_ids.mapped('total_contracted'))
            else:
                line.total_contracted = line.quantity_contracted * line.unit_price

    @api.depends(
        'progress_ids.quantity_executed', 'quantity_contracted', 'unit_price', 'total_contracted',
        'child_ids.quantity_executed_cumulative', 'child_ids.amount_executed_cumulative',
    )
    def _compute_execution(self):
        for line in self.sorted(key=lambda l: l.level, reverse=True):
            if line.child_ids:
                qty_exec = sum(line.child_ids.mapped('quantity_executed_cumulative'))
                amount_exec = sum(line.child_ids.mapped('amount_executed_cumulative'))
            else:
                qty_exec = sum(line.progress_ids.mapped('quantity_executed'))
                amount_exec = qty_exec * line.unit_price
            line.quantity_executed_cumulative = qty_exec
            line.amount_executed_cumulative = amount_exec
            if line.total_contracted:
                line.percentage_complete = round((amount_exec / line.total_contracted) * 100, 2)
            elif line.quantity_contracted:
                line.percentage_complete = round((qty_exec / line.quantity_contracted) * 100, 2)
            else:
                line.percentage_complete = 0.0

    # ---------------------------------------------------------------
    # Constraints
    # ---------------------------------------------------------------
    @api.constrains('tender_id', 'project_id')
    def _check_single_owner(self):
        for line in self:
            if bool(line.tender_id) == bool(line.project_id):
                raise ValidationError(
                    'كل بند BOQ لازم يبقى تابع لمناقصة واحدة أو مشروع واحد، مش الاتنين ولا ولا حاجة.'
                )

    @api.constrains('parent_id')
    def _check_not_self_parent(self):
        for line in self:
            if line.parent_id and line.parent_id.id == line.id:
                raise ValidationError('البند مينفعش يكون أب لنفسه.')

    @api.constrains('parent_id')
    def _check_parent_recursion(self):
        if not self._check_recursion():
            raise ValidationError('مينفعش تعمل حلقة في هيكل البنود (بند يبقى أب لنفسه بشكل غير مباشر).')

    @api.constrains('quantity_contracted', 'unit_price')
    def _check_non_negative(self):
        for line in self:
            if float_compare(line.quantity_contracted, 0.0, precision_digits=4) < 0:
                raise ValidationError('الكمية المتعاقد عليها لازم تكون صفر أو أكبر.')
            if float_compare(line.unit_price, 0.0, precision_digits=4) < 0:
                raise ValidationError('سعر الوحدة لازم يكون صفر أو أكبر.')

    @api.constrains('parent_id', 'tender_id', 'project_id')
    def _check_parent_same_owner(self):
        for line in self:
            if line.parent_id:
                if line.tender_id and line.parent_id.tender_id != line.tender_id:
                    raise ValidationError('البند الفرعي لازم يتبع نفس المناقصة اللي البند الأب تابع لها.')
                if line.project_id and line.parent_id.project_id != line.project_id:
                    raise ValidationError('البند الفرعي لازم يتبع نفس المشروع اللي البند الأب تابع له.')

    # ---------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------
    def _copy_tree_to_project(self, project, parent=None):
        """Recursively duplicate this BOQ line (and its children) onto a project.
        Used when a won tender is converted into an execution project."""
        self.ensure_one()
        new_line = self.create({
            'project_id': project.id,
            'tender_id': False,
            'parent_id': parent.id if parent else False,
            'sequence': self.sequence,
            'code': self.code,
            'name': self.name,
            'uom_id': self.uom_id.id,
            'quantity_contracted': self.quantity_contracted,
            'unit_price': self.unit_price,
            'analytic_account_id': self.analytic_account_id.id,
        })
        for child in self.child_ids:
            child._copy_tree_to_project(project, parent=new_line)
        return new_line