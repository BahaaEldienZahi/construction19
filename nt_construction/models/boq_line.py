from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare


class BoqLine(models.Model):
    _name = 'boq.line'
    _description = 'BOQ Line (Bill of Quantities)'
    _check_company_auto = True
    _parent_name = 'parent_id'
    _parent_store = True
    _order = 'parent_path, sequence, id'
    _rec_name = 'name'

    # ---------------------------------------------------------------
    # Ownership: a BOQ line belongs to a Tender (as-bid) OR a Project
    # (as-contracted / as-built). Never both.
    # ---------------------------------------------------------------
    tender_id = fields.Many2one(
        'tender.tender',
        ondelete='cascade', index=True,
        check_company=True,
    )
    project_id = fields.Many2one(
        'project.project',
        ondelete='cascade', index=True,
        check_company=True,
    )
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
    )
    # contract currency: project's, else tender's, else company's (multi-currency, step 3)
    currency_id = fields.Many2one(
        'res.currency', compute='_compute_currency_id', store=True,
    )

    # ---------------------------------------------------------------
    # Hierarchy: Chapter -> Item -> Sub-item
    # ---------------------------------------------------------------
    parent_id = fields.Many2one(
        'boq.line', string='Parent Line',
        ondelete='cascade', index=True,
        check_company=True,
    )
    child_ids = fields.One2many('boq.line', 'parent_id', string='Sub Lines')
    parent_path = fields.Char(index=True)
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
    unit_price = fields.Monetary(currency_field='currency_id', groups='nt_construction.group_construction_see_amounts,project.group_project_manager')

    total_contracted = fields.Monetary(
        currency_field='currency_id',
        compute='_compute_total_contracted', store=True, recursive=True,
        groups='nt_construction.group_construction_see_amounts,project.group_project_manager',
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
        groups='nt_construction.group_construction_see_amounts,project.group_project_manager',
    )
    percentage_complete = fields.Float(
        string='% Complete', compute='_compute_execution', store=True, recursive=True,
    )
    # reported by site engineers in confirmed daily reports (informational, not executed)
    quantity_reported_cumulative = fields.Float(
        string='Reported Qty (Daily Reports)', compute='_compute_reported', store=True,
        digits='Product Unit of Measure', recursive=True,
    )
    # ---------------------------------------------------------------
    # Certified (billed to the client): approved client certificates (DECISIONS A8)
    # ---------------------------------------------------------------
    certificate_line_ids = fields.One2many('boq.payment.certificate.line', 'boq_line_id')
    quantity_certified_cumulative = fields.Float(
        string='Certified Qty (Cumulative)', compute='_compute_certified', store=True,
        digits='Product Unit of Measure', recursive=True,
    )
    amount_certified_cumulative = fields.Monetary(
        string='Certified Value (Cumulative)', currency_field='currency_id',
        compute='_compute_certified', store=True, recursive=True,
        groups='nt_construction.group_construction_see_amounts,project.group_project_manager',
    )

    # ---------------------------------------------------------------
    # Optional linkage to execution tracking
    # ---------------------------------------------------------------
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        help='لتتبع التكلفة الفعلية (مواد/عمالة/مقاولين باطن) المرتبطة بالبند ده',
        check_company=True,
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
        groups='nt_construction.group_construction_see_amounts,project.group_project_manager',
    )

    @api.depends(
        'po_line_ids.price_subtotal', 'po_line_ids.order_id.state',
        'subcontract_line_ids.subtotal', 'subcontract_line_ids.agreement_id.state',
    )
    def _compute_committed_amount(self):
        # PO lines are converted into the BOQ (contract) currency at the order date
        for line in self:
            confirmed_po = line.po_line_ids.filtered(lambda pol: pol.order_id.state in ('purchase', 'done'))
            approved_sub = line.subcontract_line_ids.filtered(lambda sl: sl.agreement_id.state == 'approved')
            target = line.currency_id or line.company_id.currency_id
            po_total = sum(
                pol.currency_id._convert(
                    pol.price_subtotal, target, pol.company_id,
                    pol.order_id.date_order or fields.Date.context_today(line))
                for pol in confirmed_po
            )
            sub_total = sum(
                sl.currency_id._convert(sl.subtotal, target, line.company_id, sl.agreement_id.date)
                for sl in approved_sub
            )
            line.committed_amount = po_total + sub_total

    @api.depends('project_id.construction_currency_id', 'tender_id.currency_id', 'company_id.currency_id')
    def _compute_currency_id(self):
        for line in self:
            line.currency_id = (line.project_id.construction_currency_id or line.tender_id.currency_id
                                or line.company_id.currency_id)

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
        for line in self.sorted(key=lambda rec: rec.level, reverse=True):
            if line.child_ids:
                line.total_contracted = sum(line.child_ids.mapped('total_contracted'))
            else:
                line.total_contracted = line.quantity_contracted * line.unit_price

    @api.depends(
        'progress_ids.quantity_executed', 'progress_ids.work_measurement_id.state',
        'quantity_contracted', 'unit_price', 'total_contracted',
        'child_ids.quantity_executed_cumulative', 'child_ids.amount_executed_cumulative',
    )
    def _compute_execution(self):
        # executed = confirmed measurements only (DECISIONS A8, UX_SPEC 3.0)
        for line in self.sorted(key=lambda rec: rec.level, reverse=True):
            if line.child_ids:
                qty_exec = sum(line.child_ids.mapped('quantity_executed_cumulative'))
                amount_exec = sum(line.child_ids.mapped('amount_executed_cumulative'))
            else:
                measured = line.progress_ids.filtered(
                    lambda p: p.work_measurement_id.state in ('confirmed', 'linked'))
                qty_exec = sum(measured.mapped('quantity_executed'))
                amount_exec = qty_exec * line.unit_price
            line.quantity_executed_cumulative = qty_exec
            line.amount_executed_cumulative = amount_exec
            if line.total_contracted:
                line.percentage_complete = round((amount_exec / line.total_contracted) * 100, 2)
            elif line.quantity_contracted:
                line.percentage_complete = round((qty_exec / line.quantity_contracted) * 100, 2)
            else:
                line.percentage_complete = 0.0

    @api.depends('progress_ids.quantity_executed', 'progress_ids.daily_report_id.state',
                 'child_ids.quantity_reported_cumulative')
    def _compute_reported(self):
        for line in self.sorted(key=lambda rec: rec.level, reverse=True):
            if line.child_ids:
                line.quantity_reported_cumulative = sum(line.child_ids.mapped('quantity_reported_cumulative'))
            else:
                line.quantity_reported_cumulative = sum(line.progress_ids.filtered(
                    lambda p: p.daily_report_id.state == 'confirmed').mapped('quantity_executed'))

    @api.depends('certificate_line_ids.quantity_this_period', 'certificate_line_ids.amount_this_period',
                 'certificate_line_ids.certificate_id.state',
                 'child_ids.quantity_certified_cumulative', 'child_ids.amount_certified_cumulative')
    def _compute_certified(self):
        for line in self.sorted(key=lambda rec: rec.level, reverse=True):
            if line.child_ids:
                line.quantity_certified_cumulative = sum(line.child_ids.mapped('quantity_certified_cumulative'))
                line.amount_certified_cumulative = sum(line.child_ids.mapped('amount_certified_cumulative'))
            else:
                approved = line.certificate_line_ids.filtered(lambda cl: cl.certificate_id.state == 'approved')
                line.quantity_certified_cumulative = sum(approved.mapped('quantity_this_period'))
                line.amount_certified_cumulative = sum(approved.mapped('amount_this_period'))

    # ---------------------------------------------------------------
    # Constraints
    # ---------------------------------------------------------------
    # @api.constrains('tender_id', 'project_id')
    # def _check_single_owner(self):
    #     for line in self:
    #         if bool(line.tender_id) == bool(line.project_id):
    #             raise ValidationError(
    #                 'كل بند BOQ لازم يبقى تابع لمناقصة واحدة أو مشروع واحد، مش الاتنين ولا ولا حاجة.'
    #             )

    @api.constrains('parent_id')
    def _check_not_self_parent(self):
        for line in self:
            if line.parent_id and line.parent_id.id == line.id:
                raise ValidationError(self.env._('A BOQ line cannot be its own parent.'))

    @api.constrains('parent_id')
    def _check_parent_recursion(self):
        if self._has_cycle():
            raise ValidationError(self.env._('You cannot create a loop in the BOQ hierarchy.'))

    @api.constrains('quantity_contracted', 'unit_price')
    def _check_non_negative(self):
        for line in self:
            if float_compare(line.quantity_contracted, 0.0, precision_digits=4) < 0:
                raise ValidationError(self.env._('The contracted quantity must be zero or more.'))
            if float_compare(line.unit_price, 0.0, precision_digits=4) < 0:
                raise ValidationError(self.env._('The unit price must be zero or more.'))

    @api.constrains('parent_id', 'tender_id', 'project_id')
    def _check_parent_same_owner(self):
        for line in self:
            if line.parent_id:
                if line.tender_id and line.parent_id.tender_id != line.tender_id:
                    raise ValidationError(self.env._('A sub-line must belong to the same tender as its parent line.'))
                if line.project_id and line.parent_id.project_id != line.project_id:
                    raise ValidationError(self.env._('A sub-line must belong to the same project as its parent line.'))

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
