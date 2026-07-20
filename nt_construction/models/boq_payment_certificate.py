# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare


class BoqPaymentCertificate(models.Model):
    _name = 'boq.payment.certificate'
    _description = 'BOQ Payment Certificate (Progress Billing)'
    _inherit = ['construction.approval.mixin', 'mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(default=lambda self: _('New'), readonly=True, copy=False)
    project_id = fields.Many2one(
        'project.project', string='Project', required=True,
        domain=[('is_construction_project', '=', True)], tracking=True,
    )
    date = fields.Date(default=fields.Date.context_today, required=True)
    period_from = fields.Date(string='Period From')
    period_to = fields.Date(string='Period To')
    currency_id = fields.Many2one(related='project_id.construction_currency_id', readonly=True)

    line_ids = fields.One2many('boq.payment.certificate.line', 'certificate_id', string='Lines')

    gross_amount = fields.Monetary(
        string='Gross Amount', currency_field='currency_id',
        compute='_compute_amounts', store=True,
    )
    retention_percentage = fields.Float(
        related='project_id.retention_percentage', readonly=True,
    )
    retention_amount = fields.Monetary(
        string='Retention Held', currency_field='currency_id',
        compute='_compute_amounts', store=True,
    )
    advance_recovery_amount = fields.Monetary(
        string='Advance Recovery', currency_field='currency_id',
        help='المبلغ المسترد من الدفعة المقدمة في المستخلص ده',
    )
    net_payable = fields.Monetary(
        string='Net Payable', currency_field='currency_id',
        compute='_compute_amounts', store=True,
    )
    move_id = fields.Many2one('account.move', string='Customer Invoice', readonly=True, copy=False)
    move_state = fields.Selection(related='move_id.state', string='Invoice Status')



    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('boq.payment.certificate') or _('New')
        return super().create(vals_list)

    @api.depends('line_ids.amount_this_period', 'retention_percentage', 'advance_recovery_amount')
    def _compute_amounts(self):
        for cert in self:
            gross = sum(cert.line_ids.mapped('amount_this_period'))
            cert.gross_amount = gross
            cert.retention_amount = gross * (cert.retention_percentage / 100.0)
            cert.net_payable = gross - cert.retention_amount - cert.advance_recovery_amount

    def _on_final_approval(self):
        for cert in self:
            for line in cert.line_ids:
                self.env['boq.line.progress'].create({
                    'boq_line_id': line.boq_line_id.id,
                    'date': cert.date,
                    'period_name': cert.name,
                    'quantity_executed': line.quantity_this_period,
                    'note': _('Auto-created from Payment Certificate %s') % cert.name,
                })

    def action_load_from_wm(self):
        """Open wizard to select a confirmed Work Measurement and auto-fill certificate lines."""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_('Can only load from Work Measurement when the certificate is in draft state.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Load from Work Measurement'),
            'res_model': 'load.certificate.from.wm.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_certificate_id': self.id},
        }

    def action_view_invoice(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Customer Invoice'),
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.move_id.id,
        }

    def action_create_invoice(self):
        self.ensure_one()
        if self.state != 'approved':
            raise UserError(_('Only approved certificates can be invoiced.'))
        if self.move_id:
            raise UserError(_('This certificate already has a linked invoice.'))
        if float_compare(self.net_payable, 0.0, precision_digits=2) <= 0:
            raise UserError(_('Net payable amount must be positive to create an invoice.'))

        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.project_id.partner_id.id,
            'invoice_date': self.date,
            'invoice_origin': self.name,
            'invoice_line_ids': [(0, 0, {
                'name': _('%s - %s (Net after %.1f%% retention & advance recovery)') % (
                    self.name, self.project_id.name, self.retention_percentage),
                'quantity': 1,
                'price_unit': self.net_payable,
            })],
        })
        self.move_id = move.id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Customer Invoice'),
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': move.id,
        }


class BoqPaymentCertificateLine(models.Model):
    _name = 'boq.payment.certificate.line'
    _description = 'BOQ Payment Certificate Line'

    certificate_id = fields.Many2one(
        'boq.payment.certificate', required=True, ondelete='cascade', index=True,
    )
    project_id = fields.Many2one(related='certificate_id.project_id', store=True)
    currency_id = fields.Many2one(related='certificate_id.currency_id', readonly=True)

    boq_line_id = fields.Many2one(
        'boq.line', string='BOQ Line', required=True,
        domain="[('project_id', '=', project_id), ('is_group', '=', False)]",
    )
    unit_price = fields.Monetary(
        related='boq_line_id.unit_price', string='Unit Price', readonly=True,
    )
    quantity_contracted = fields.Float(
        related='boq_line_id.quantity_contracted', string='Contracted Qty', readonly=True,
    )
    cumulative_qty_before = fields.Float(
        string='Cumulative Before', compute='_compute_cumulative_before', digits='Product Unit of Measure',
    )
    quantity_this_period = fields.Float(
        string='Qty This Period', required=True, digits='Product Unit of Measure',
    )
    cumulative_qty_after = fields.Float(
        string='Cumulative After', compute='_compute_cumulative_before', digits='Product Unit of Measure',
    )
    amount_this_period = fields.Monetary(
        string='Amount', currency_field='currency_id',
        compute='_compute_amount_this_period', store=True,
    )

    @api.depends('boq_line_id', 'quantity_this_period')
    def _compute_cumulative_before(self):
        for line in self:
            line.cumulative_qty_before = line.boq_line_id.quantity_executed_cumulative
            line.cumulative_qty_after = line.cumulative_qty_before + line.quantity_this_period

    @api.depends('quantity_this_period', 'unit_price')
    def _compute_amount_this_period(self):
        for line in self:
            line.amount_this_period = line.quantity_this_period * line.unit_price

    @api.constrains('quantity_this_period', 'boq_line_id')
    def _check_not_exceeding_contracted(self):
        for line in self:
            if line.boq_line_id.quantity_contracted and \
                    line.cumulative_qty_after > line.boq_line_id.quantity_contracted * 1.001:
                raise ValidationError(_(
                    'الكمية التراكمية بعد المستخلص ده (%.2f) هتتخطى الكمية المتعاقد عليها (%.2f) للبند "%s".'
                ) % (line.cumulative_qty_after, line.boq_line_id.quantity_contracted, line.boq_line_id.name))
