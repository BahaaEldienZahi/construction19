from odoo import Command, api, fields, models
from odoo.exceptions import UserError


class WorkMeasurement(models.Model):
    """Work Measurement groups daily reports into billing periods."""
    _name = 'work.measurement'
    _description = 'Work Measurement (BOQ Execution Tracking)'
    _check_company_auto = True
    _inherit = ['construction.workflow.guard', 'mail.thread', 'mail.activity.mixin']
    _workflow_guarded_fields = ('state', 'payment_certificate_id')
    _order = 'date desc, id desc'

    name = fields.Char(default=lambda self: self.env._('New'), readonly=True, copy=False)
    project_id = fields.Many2one(
        'project.project', required=True,
        domain=[('is_construction_project', '=', True)], tracking=True,
        check_company=True,
    )
    company_id = fields.Many2one(related='project_id.company_id', store=True, readonly=True)
    currency_id = fields.Many2one(related='project_id.construction_currency_id', readonly=True)
    date = fields.Date(default=fields.Date.context_today, required=True)
    period_from = fields.Date()
    period_to = fields.Date()

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
        'boq.payment.certificate',
        readonly=True, copy=False,
        check_company=True,
    )
    progress_ids = fields.One2many(
        'boq.line.progress', 'work_measurement_id', string='Progress Entries',
    )
    total_executed_value = fields.Monetary(
        currency_field='currency_id',
        compute='_compute_total_executed', store=True,
        groups='nt_construction.group_construction_see_amounts,project.group_project_manager',
    )

    _name_uniq = models.Constraint(
        'unique(name, company_id)',
        'Work measurement reference must be unique per company!',
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', self.env._('New')) == self.env._('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('work.measurement') or self.env._('New')
        return super().create(vals_list)

    daily_report_count = fields.Integer(compute='_compute_daily_report_count')

    @api.depends('progress_ids.quantity_executed', 'progress_ids.boq_line_id.unit_price')
    def _compute_total_executed(self):
        # value of the quantities measured here (executed = measured, DECISIONS F1)
        for wm in self:
            wm.total_executed_value = sum(
                prog.quantity_executed * prog.boq_line_id.unit_price for prog in wm.sudo().progress_ids)

    def _compute_daily_report_count(self):
        for wm in self:
            wm.daily_report_count = len(wm.daily_report_ids)

    def action_confirm(self):
        self._check_construction_role('nt_construction.group_construction_quantity_surveyor')
        for wm in self:
            if wm.state != 'draft':
                raise UserError(self.env._('Only draft measurements can be confirmed.'))
        self._workflow_write({'state': 'confirmed'})

    def action_reset_draft(self):
        self._check_construction_role('nt_construction.group_construction_quantity_surveyor')
        if any(wm.state == 'linked' or wm.payment_certificate_id for wm in self):
            # DECISIONS Q6: a measurement already billed cannot be reopened
            raise UserError(self.env._('A measurement linked to a payment certificate cannot be reset to draft.'))
        self._workflow_write({'state': 'draft'})

    # ------------------------------------------------------------------
    # Golden cycle: measurement -> client certificate
    # ------------------------------------------------------------------
    def action_create_certificate(self):
        """Draft client certificate whose total to date per item is the quantity measured to date
        (confirmed measurements, capped at the contracted quantity). The confirmed measurements of the
        project not yet billed are attached to it and become *linked* when it is approved."""
        self._check_construction_role('nt_construction.group_construction_quantity_surveyor')
        project = self.project_id
        if len(project) != 1:
            raise UserError(self.env._('Select measurements of a single project.'))
        if any(wm.state != 'confirmed' or wm.payment_certificate_id for wm in self):
            raise UserError(self.env._('Only confirmed measurements not yet on a certificate can be certified.'))
        Certificate = self.env['boq.payment.certificate']
        open_cert = Certificate.search([('project_id', '=', project.id),
                                        ('state', 'in', ('draft', 'submitted', 'approved_l1'))], limit=1)
        if open_cert:
            raise UserError(self.env._(
                '%(cert)s is still open on this project. Approve, reject or cancel it first.', cert=open_cert.name))
        measurements = self.search([('project_id', '=', project.id), ('state', '=', 'confirmed'),
                                    ('payment_certificate_id', '=', False)])
        items = self.env['boq.line'].sudo().search(
            [('project_id', '=', project.id), ('is_group', '=', False)], order='sequence, id')
        lines = []
        for item in items:
            total = min(item.quantity_executed_cumulative, item.quantity_contracted or item.quantity_executed_cumulative)
            if total > item.quantity_certified_cumulative:
                lines.append(Command.create({'boq_line_id': item.id, 'quantity_total': total}))
        if not lines:
            raise UserError(self.env._('Nothing to certify: every measured quantity is already certified.'))
        dates = measurements.mapped('period_from') + measurements.mapped('period_to') + measurements.mapped('date')
        dates = [d for d in dates if d]
        certificate = Certificate.create({
            'project_id': project.id,
            'period_from': min(dates) if dates else False,
            'period_to': max(dates) if dates else False,
            'line_ids': lines,
        })
        measurements.sudo()._workflow_write({'payment_certificate_id': certificate.id})
        return certificate._get_records_action(name=self.env._('Payment Certificate'))

    def action_view_certificate(self):
        self.ensure_one()
        return self.payment_certificate_id._get_records_action(name=self.env._('Payment Certificate'))

    def action_view_daily_reports(self):
        self.ensure_one()
        return self.daily_report_ids._get_records_action(name=self.env._('Daily Reports'))

    def action_view_project(self):
        self.ensure_one()
        return self.project_id._get_records_action(name=self.env._('Project'))
