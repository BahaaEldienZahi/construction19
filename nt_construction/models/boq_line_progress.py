# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class BoqLineProgress(models.Model):
    _name = 'boq.line.progress'
    _description = 'BOQ Line Progress Entry'
    _order = 'date desc, id desc'

    boq_line_id = fields.Many2one(
        'boq.line', string='BOQ Line', required=True, ondelete='cascade', index=True,
    )
    project_id = fields.Many2one(
        related='boq_line_id.project_id', string='Project', store=True, readonly=True,
    )
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    period_name = fields.Char(string='Period / Certificate Ref', help='مثال: مستخلص رقم 3')
    quantity_executed = fields.Float(
        string='Executed Qty (This Period)', digits='Product Unit of Measure', required=True,
    )
    note = fields.Text(string='Notes')
    user_id = fields.Many2one('res.users', string='Recorded By', default=lambda self: self.env.user)
    company_id = fields.Many2one(related='boq_line_id.company_id', store=True, readonly=True)
    daily_report_id = fields.Many2one(
        'site.daily.report', string='Site Daily Report', ondelete='set null', index=True,
        help='التقرير اليومي (السركي) اللي اتسجلت فيه الكمية دي، لو موجود',
    )

    @api.constrains('boq_line_id')
    def _check_leaf_line_only(self):
        for rec in self:
            if rec.boq_line_id.child_ids:
                raise ValidationError(
                    'مينفعش تسجل إنجاز على بند رئيسي (Chapter) - سجل الإنجاز على البنود الفرعية بس.'
                )

    @api.constrains('quantity_executed', 'boq_line_id')
    def _check_cumulative_not_exceeding(self):
        for rec in self:
            line = rec.boq_line_id
            other_entries = line.progress_ids - rec
            cumulative = sum(other_entries.mapped('quantity_executed')) + rec.quantity_executed
            if line.quantity_contracted and cumulative > line.quantity_contracted * 1.001:
                raise ValidationError(
                    'إجمالي الكمية المنفذة (%.2f) هيتعدى الكمية المتعاقد عليها (%.2f) للبند "%s". '
                    'راجع الأرقام أو عدّل الكمية المتعاقد عليها لو فيه Variation Order.'
                    % (cumulative, line.quantity_contracted, line.name)
                )