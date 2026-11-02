from odoo import api, fields, models
from odoo.exceptions import UserError


class WorkMeasurement(models.Model):
    """Work Measurement groups daily reports into billing periods."""
    _name = 'work.measurement'
    _description = 'Work Measurement (BOQ Execution Tracking)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(default=lambda self: self.env._('New'), readonly=True, copy=False)
    project_id = fields.Many2one(
        'project.project', required=True,
        domain=[('is_construction_project', '=', True)], tracking=True,
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
    )
    progress_ids = fields.One2many(
        'boq.line.progress', 'work_measurement_id', string='Progress Entries',
    )
    total_executed_value = fields.Monetary(
        currency_field='currency_id',
        compute='_compute_total_executed', store=True,
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

    @api.depends('daily_report_ids', 'daily_report_ids.progress_ids')
    def _compute_total_executed(self):
        for wm in self:
            total = 0.0
            for report in wm.daily_report_ids:
                for prog in report.progress_ids:
                    total += prog.quantity_executed * prog.boq_line_id.unit_price
            wm.total_executed_value = total

    def action_confirm(self):
        for wm in self:
            if wm.state != 'draft':
                raise UserError(self.env._('Only draft measurements can be confirmed.'))
        self.write({'state': 'confirmed'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})
