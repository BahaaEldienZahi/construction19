# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ProjectProject(models.Model):
    _inherit = 'project.project'

    # --------------------------------------------------------------
    # Tender linkage
    # --------------------------------------------------------------
    tender_id = fields.Many2one(
        'tender.tender',
        string='Source Tender',
        readonly=True,
        copy=False,
    )
    tender_reference = fields.Char(
        related='tender_id.name', string='Tender Reference', store=True, readonly=True,
    )

    # --------------------------------------------------------------
    # Contract info
    # --------------------------------------------------------------
    is_construction_project = fields.Boolean(
        string='Construction Project', default=False,
        help='فعلهال للشمر؈عة اللق هتابع فيهال (BOQق, مستخلصة, إسع ا)ؤ',
    )
    construction_type = fields.Selection([
        ('residential', 'Residential'),
        ('commercial', 'Commercial'),
        ('industrial', 'Industrial'),
        ('infrastructure', 'Infrastructure'),
    ], string='Construction Type')

    execution_type = fields.Selection([
        ('internal', 'Internal'),
        ('subcontract', 'Subcontract'),
        ('joint_venture', 'Joint Venture'),
        ('supply_install', 'Supply & Install'),
        ('management', 'Management Only'),
    ], string='Execution Type', default='internal', tracking=True,
       help='نوع التننبع: دستي, مقاول باطن, مرظرو مشبيك, بومبة وقرياب, إاعاب قطا')

    client_po_number = fields.Char(string='Client PO Number')
    contract_number = fields.Char(string='Contract Number', copy=False)
    contract_signing_date = fields.Date(string='Contract Signing Date')

    contract_value = fields.Monetary(
        string='Contract Value',
        currency_field='construction_currency_id',
        help='القيمة التعاقدية بعد الرٌسية (ممنن تححي اسbرع باسوام التوعييد - Variation Orders)',
    )
    construction_currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
        help='عملة العقد. تةاصا قطايان من عملة الماقشص٩ وو “ لرظروااحول من مناقشطة إط ع عملة ال؈رغمة',
    )

    site_start_date = fields.Date(string='Site Handover / Start Date')
    site_completion_date = fields.Date(string='Contractual Completion Date')
    actual_completion_date = fields.Date(string='Actual Completion Date', copy=False)

    site_location = fields.Text(
        string='Site Address',
        help='ع؍وحن الموقوع الفلدي للتنوث쀹 ل؈ محبلن عن عونان العميل',
    )
    consultant_id = fields.Many2one(
        'res.partner', string='Supervising Consultant',
        help='الاستعاري المضaؘ�ف علدم التنوة',
    )

    # --------------------------------------------------------------
    # Retention / advance payment terms (تسعمللا واشار لالمستخلصة)
    # --------------------------------------------------------------
    retention_percentage = fields.Float(
        string='Retention %', default=5.0,
        help='نسبة الضمان المححبية من كل مستخلص',
    )
    advance_payment_percentage = fields.Float(
        string='Advance Payment %', default=0.0,
        help='نسبة الدفعة المقدمة إق بثعصل دق من المستخلصاة',
    )

    # --------------------------------------------------------------
    # Progress (مر"�شيلل احلل إ إآ BOQ اجعمل - تححر*
    #     بعد لالت tasks ـفقدن مبجان)
    # --------------------------------------------------------------
    task_progress_percentage = fields.Float(
        string='Task-based Progress %',
        compute='_compute_task_progress_percentage',
        help='نسبة إاناز,ة تقريبة بنناя المطامئ, المقصولة اسعؤ القمية الفلعية واسعؤ بحالية',
    )

    boq_line_ids = fields.One2many(
        'boq.line', 'project_id', string='BOQ Lines',
        domain=[('parent_id', '=', False)],
    )
    boq_total_contracted = fields.Monetary(
        string='BOQ Total', currency_field='construction_currency_id',
        compute='_compute_boq_total_contracted', store=True,
    )
    boq_percentage_complete = fields.Float(
        string='BOQ Progress %',
        compute='_compute_boq_percentage_complete', store=True,
    )
    boq_line_count = fields.Integer(compute='_compute_boq_line_count')

    @api.depends('boq_line_ids.total_contracted')
    def _compute_boq_total_contracted(self):
        for project in self:
            project.boq_total_contracted = sum(project.boq_line_ids.mapped('total_contracted'))

    @api.depends('boq_line_ids.amount_executed_cumulative', 'boq_total_contracted')
    def _compute_boq_percentage_complete(self):
        for project in self:
            executed = sum(project.boq_line_ids.mapped('amount_executed_cumulative'))
            project.boq_percentage_complete = (
                round((executed / project.boq_total_contracted) * 100, 2)
                if project.boq_total_contracted else 0.0
            )

    @api.depends('task_ids.stage_id', 'task_ids.stage_id.fold')
    def _compute_task_progress_percentage(self):
        # A stage being "folded" (e.g. Done/Cancelled) is the standard, locale- and
        # customization-independent way to identify a closed task in Odoo's kanban stages.
        for project in self:
            total = len(project.task_ids)
            if not total:
                project.task_progress_percentage = 0.0
                continue
            closed = len(project.task_ids.filtered(lambda t: t.stage_id.fold))
            project.task_progress_percentage = round((closed / total) * 100, 2)

    # --------------------------------------------------------------
    # Smart buttons
    # --------------------------------------------------------------
    def action_view_tender(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Tender',
            'res_model': 'tender.tender',
            'view_mode': 'form',
            'res_id': self.tender_id.id,
        }

    def _compute_boq_line_count(self):
        for project in self:
            project.boq_line_count = self.env['boq.line'].search_count(
                [('project_id', '=', project.id)])

    def action_view_boq(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Bill of Quantities',
            'res_model': 'boq.line',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    # --------------------------------------------------------------
    # Subcontracting
    # --------------------------------------------------------------
    subcontract_agreement_ids = fields.One2many(
        'subcontract.agreement', 'project_id', string='Subcontract Agreements',
    )
    subcontract_agreement_count = fields.Integer(compute='_compute_subcontract_agreement_count')
    total_subcontracted_committed = fields.Monetary(
        string='Total Subcontracted (Approved)', currency_field='construction_currency_id',
        compute='_compute_total_subcontracted_committed',
    )

    def _compute_subcontract_agreement_count(self):
        for project in self:
            project.subcontract_agreement_count = self.env['subcontract.agreement'].search_count(
                [('project_id', '=', project.id)])

    @api.depends('subcontract_agreement_ids.contract_value', 'subcontract_agreement_ids.state')
    def _compute_total_subcontracted_committed(self):
        for project in self:
            approved = project.subcontract_agreement_ids.filtered(lambda a: a.state == 'approved')
            project.total_subcontracted_committed = sum(approved.mapped('contract_value'))

    def action_view_subcontract_agreements(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Subcontract Agreements'),
            'res_model': 'subcontract.agreement',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    # --------------------------------------------------------------
    # Site daily reports (Sarky)
    # --------------------------------------------------------------
    daily_report_ids = fields.One2many('site.daily.report', 'project_id', string='Site Daily Reports')
    daily_report_count = fields.Integer(compute='_compute_daily_report_count')

    def _compute_daily_report_count(self):
        for project in self:
            project.daily_report_count = self.env['site.daily.report'].search_count(
                [('project_id', '=', project.id)])

    def action_view_daily_reports(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Site Daily Reports'),
            'res_model': 'site.daily.report',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    # --------------------------------------------------------------
    # Material Requisitions
    # --------------------------------------------------------------
    material_requisition_count = fields.Integer(compute='_compute_material_requisition_count')

    def _compute_material_requisition_count(self):
        for project in self:
            project.material_requisition_count = self.env['material.requisition'].search_count(
                [('project_id', '=', project.id)])

    def action_view_material_requisitions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Material Requisitions'),
            'res_model': 'material.requisition',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    # --------------------------------------------------------------
    # Inventory (Stock) integration
    # --------------------------------------------------------------
    # Every construction project gets its own internal stock location
    # (a child of the company warehouse's Stock location) so materials
    # issued via Material Requisitions show up as real Inventory
    # transfers/stock moves, and on-hand quantities at the project
    # site can be tracked like any other Odoo location.
    # --------------------------------------------------------------
    stock_location_id = fields.Many2one(
        'stock.location', string='Site Stock Location', readonly=True, copy=False,
        help='لوكيان المضصون العاصن الموقع - جحولد تقطايان أؑال مƂ توقشا طلب صـف مواد',
    )
    material_transfer_count = fields.Integer(compute='_compute_material_transfer_count')

    def _compute_material_transfer_count(self):
        for project in self:
            if project.stock_location_id:
                project.material_transfer_count = self.env['stock.picking'].search_count([
                    '|',
                    ('location_id', '=', project.stock_location_id.id),
                    ('location_dest_id', '=', project.stock_location_id.id),
                ])
            else:
                project.material_transfer_count = 0

    def action_view_material_transfers(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Material Transfers'),
            'res_model': 'stock.picking',
            'view_mode': 'list,form',
            'domain': ['|', ('location_id', '=', self.stock_location_id.id),
                   ('location_dest_id', '=', self.stock_location_id.id)],
        }

    def _get_or_create_stock_location(self):
        """Return this project's site stock location, creating it (and
        registering it under the company's default warehouse) the first
        time it is needed."""
        self.ensure_one()
        if self.stock_location_id:
            return self.stock_location_id
        warehouse = self.env['stock.warehouse'].search(
            [('company_id', '=', self.company_id.id or self.env.company.id)], limit=1)
        parent_location = warehouse.lot_stock_id if warehouse else self.env.ref(
            'stock.stock_location_locations', raise_if_not_found=False)
        location = self.env['stock.location'].create({
            'name': self.name or _('Project'),
            'usage': 'internal',
            'location_id': parent_location.id if parent_location else False,
            'company_id': self.company_id.id or self.env.company.id,
        })
        self.stock_location_id = location.id
        return location

    # --------------------------------------------------------------
    # Work Inspections
    # --------------------------------------------------------------
    inspection_count = fields.Integer(compute='_compute_inspection_count')

    def _compute_inspection_count(self):
        for project in self:
            project.inspection_count = self.env['work.inspection'].search_count(
                [('project_id', '=', project.id)])

    def action_view_inspections(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Work Inspections'),
            'res_model': 'work.inspection',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    # --------------------------------------------------------------
    # Correspondence
    # --------------------------------------------------------------
    correspondence_count = fields.Integer(compute='_compute_correspondence_count')

    def _compute_correspondence_count(self):
        for project in self:
            project.correspondence_count = self.env['project.correspondence'].search_count(
                [('project_id', '=', project.id)])

    def action_view_correspondence(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Correspondence / Letters'),
            'res_model': 'project.correspondence',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    # --------------------------------------------------------------
    # Progress Photos
    # --------------------------------------------------------------
    photo_count = fields.Integer(compute='_compute_photo_count')

    def _compute_photo_count(self):
        for project in self:
            project.photo_count = self.env['site.progress.photo'].search_count(
                [('project_id', '=', project.id)])

    def action_view_photos(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Progress Photos'),
            'res_model': 'site.progress.photo',
            'view_mode': 'kanban,list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    # --------------------------------------------------------------
    # Bank Guarantees
    # --------------------------------------------------------------
    guarantee_count = fields.Integer(compute='_compute_guarantee_count')

    def _compute_guarantee_count(self):
        for project in self:
            project.guarantee_count = self.env['bank.guarantee'].search_count(
                [('project_id', '=', project.id)])

    def action_view_guarantees(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Bank Guarantees'),
            'res_model': 'bank.guarantee',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    # --------------------------------------------------------------
    # Handover / Delivery
    # --------------------------------------------------------------
    handover_ids = fields.One2many('project.handover', 'project_id', string='Handovers')
    handover_count = fields.Integer(compute='_compute_handover_count')
    retention_held_amount = fields.Monetary(
        string='Retention Held (Client Side)', currency_field='construction_currency_id',
        compute='_compute_retention_held_amount',
    )

    def _compute_handover_count(self):
        for project in self:
            project.handover_count = self.env['project.handover'].search_count(
                [('project_id', '=', project.id)])

    @api.depends('boq_line_ids')
    def _compute_retention_held_amount(self):
        for project in self:
            certs = self.env['boq.payment.certificate'].search([
                ('project_id', '=', project.id),
                ('state', '=', 'approved'),
            ])
            project.retention_held_amount = sum(certs.mapped('retention_amount'))

    def action_view_handovers(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Handover / Delivery'),
            'res_model': 'project.handover',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }
