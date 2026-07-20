# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare


class SubcontractPaymentCertificate(models.Model):
    """مستخلص مقاول الباطن: يماثل مستخلص العميل لكنه موجه للمقاولين الباطن"""
    _name = 'subcontract.payment.certificate'
    _description = 'Subcontractor Payment Certificate'
    _inherit = ['construction.approval.mixin', 'mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(default=lambda self: _('New'), readonly=True, copy=False)
    subcontract_agreement_id = fields.Many2one(
        'subcontract.agreement', string='Subcontract Agreement', required=True,
        domain="[('state', '=', 'approved')]", tracking=True,
    )
    project_id = fields.Many2one(related='subcontract_agreement_id.project_id', store=True, readonly=True)
    partner_id = fields.Many2one(related='subcontract_agreement_id.partner_id', store=True, readonly=True)
    company_id = fields.Many2one(related='subcontract_agreement_id.company_id', store=True, readonly=True)
    currency_id = fields.Many2one(related='subcontract_agreement_id.currency_id', readonly=True)
    date = fields.Date(default=fields.Date.context_today, required=True)
    period_from = fields.Date(string='Period From')
    period_to = fields.Date(string='Period To')

    line_ids = fields.One2many('subcontract.payment.certificate.line', 'certificate_id', string='Lines')

    gross_amount = fields.Monetary(
        string='Gross Amount', currency_field='currency_id',
        compute='_compute_amounts', store=True,
    )
    retention_percentage = fields.Float(
        related='subcontract_agreement_id.retention_percentage', readonly=True,
    )
    retention_amount = fields.Monetary(
        string='Retention Held', currency_field='currency_id',
        compute='_compute_amounts', store=True,
    )
    net_payable = fields.Monetary(
        string='Net Payable', currency_field='currency_id',
        compute='_compute_amounts', store=True,
    )
    move_id = fields.Many2one('account.move', string='Vendor Bill', readonly=True, copy=False)
    move_state = fields.Selection(related='move_id.state', string='Bill Status')

    _sql_constraints = [
        ('name_uniq', 'unique(name, company_id)', 'Certificate reference must be unique per company!'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('subcontract.payment.certificate') or _('New')
        return super().create(vals_list)

    @api.depends('line_ids.amount_this_period', 'retention_percentage')
    def _compute_amounts(self):
        for cert in self:
            gross = sum(cert.line_ids.mapped('amount_this_period'))
            cert.gross_amount = gross
            cert.retention_amount = gross * (cert.retention_percentage / 100.0)
            cert.net_payable = gross - cert.retention_amount

    def _on_final_approval(self):
        pass  # Override to not auto-create progress — subcontractor certs don't create BOQ progress

    def action_view_bill(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Vendor Bill'),
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.move_id.id,
        }

    def action_create_vendor_bill(self):
        self.ensure_one()
        if self.state != 'approved':
            raise UserError(_('Only approved certificates can be converted to a vendor bill.'))
        if self.move_id:
            raise UserError(_('This certificate already has a linked vendor bill.'))
        if float_compare(self.net_payable, 0.0, precision_digits=2) <= 0:
            raise UserError(_('Net payable amount must be positive to create a vendor bill.'))

        move = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_id.id,
            'invoice_date': self.date,
            'invoice_origin': self.name,
            'ref': _('Subcontract Certificate: %s') % self.name,
            'invoice_line_ids': [(0, 0, {
                'name': _('%s - %s (Net after %.1f%% retention)') % (
                    self.name, self.subcontract_agreement_id.partner_id.name, self.retention_percentage),
                'quantity': 1,
                'price_unit': self.net_payable,
            })],
        })
        self.move_id = move.id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Vendor Bill'),
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': move.id,
        }


class SubcontractPaymentCertificateLine(models.Model):
    _name = 'subcontract.payment.certificate.line'
    _description = 'Subcontractor Payment Certificate Line'

    certificate_id = fields.Many2one(
        'subcontract.payment.certificate', required=True, ondelete='cascade', index=True,
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
    quantity_this_period = fields.Float(
        string='Qty This Period', required=True, digits='Product Unit of Measure',
    )
    amount_this_period = fields.Monetary(
        string='Amount', currency_field='currency_id',
        compute='_compute_amount_this_period', store=True,
    )

    @api.depends('quantity_this_period', 'unit_price')
    def _compute_amount_this_period(self):
        for line in self:
            line.amount_this_period = line.quantity_this_period * line.unit_price
