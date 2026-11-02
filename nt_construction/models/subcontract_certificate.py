from odoo import Command, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare

AMOUNT_GROUPS = 'nt_construction.group_construction_see_amounts,project.group_project_manager'


class SubcontractCertificate(models.Model):
    """Subcontractor certificate: cumulative quantities per agreement line (previous / current /
    total), retention withheld from the subcontractor -> vendor bill (Cr Retention Payable)."""
    _name = 'subcontract.certificate'
    _description = 'Subcontractor Certificate'
    _check_company_auto = True
    _inherit = ['construction.approval.mixin', 'mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    _workflow_guarded_fields = (
        'state', 'approver_l1_id', 'approval_l1_date', 'approver_l2_id', 'approval_l2_date', 'move_id',
    )
    _submit_group_xmlids = (
        'nt_construction.group_construction_quantity_surveyor',
        'nt_construction.group_construction_project_manager',
    )

    name = fields.Char(default=lambda self: self.env._('New'), readonly=True, copy=False)
    agreement_id = fields.Many2one(
        'subcontract.agreement', required=True, check_company=True, tracking=True,
        domain=[('state', '=', 'approved')])
    project_id = fields.Many2one(related='agreement_id.project_id', store=True, index=True)
    partner_id = fields.Many2one(related='agreement_id.partner_id', store=True, string='Subcontractor')
    company_id = fields.Many2one(related='agreement_id.company_id', store=True, index=True)
    currency_id = fields.Many2one(related='agreement_id.currency_id')
    date = fields.Date(default=fields.Date.context_today, required=True)
    retention_percentage = fields.Float(related='agreement_id.retention_percentage')

    line_ids = fields.One2many('subcontract.certificate.line', 'certificate_id', string='Lines')
    work_amount = fields.Monetary(
        string='Current Work', currency_field='currency_id', compute='_compute_amounts', store=True,
        groups=AMOUNT_GROUPS)
    work_amount_total = fields.Monetary(
        string='Total Work to Date', currency_field='currency_id', compute='_compute_amounts', store=True,
        groups=AMOUNT_GROUPS)
    retention_amount = fields.Monetary(
        currency_field='currency_id', compute='_compute_amounts', store=True, groups=AMOUNT_GROUPS)
    vat_amount = fields.Monetary(
        string='VAT', currency_field='currency_id', compute='_compute_amounts', store=True, groups=AMOUNT_GROUPS)
    withholding_amount = fields.Monetary(
        currency_field='currency_id', compute='_compute_amounts', store=True, groups=AMOUNT_GROUPS)
    net_payable = fields.Monetary(
        currency_field='currency_id', compute='_compute_amounts', store=True, groups=AMOUNT_GROUPS)
    move_id = fields.Many2one('account.move', string='Vendor Bill', readonly=True, copy=False, check_company=True)
    move_state = fields.Selection(related='move_id.state', string='Bill Status')

    _name_uniq = models.Constraint('unique(name, company_id)', 'Reference must be unique per company!')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', self.env._('New')) == self.env._('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('subcontract.certificate') or self.env._('New')
        return super().create(vals_list)

    @api.depends('line_ids.amount_this_period', 'line_ids.amount_total', 'retention_percentage',
                 'company_id.construction_purchase_tax_id', 'company_id.construction_purchase_withholding_tax_id')
    def _compute_amounts(self):
        for cert in self:
            work = sum(cert.line_ids.mapped('amount_this_period'))
            retention = work * cert.retention_percentage / 100.0
            cert.work_amount = work
            cert.work_amount_total = sum(cert.line_ids.mapped('amount_total'))
            cert.retention_amount = cert.currency_id.round(retention) if cert.currency_id else retention
            vat = wht = 0.0
            taxes = cert.company_id.construction_purchase_tax_id | cert.company_id.construction_purchase_withholding_tax_id
            if taxes and work:
                for tax_res in taxes.compute_all(work, currency=cert.currency_id, partner=cert.partner_id)['taxes']:
                    if tax_res['amount'] >= 0:
                        vat += tax_res['amount']
                    else:
                        wht -= tax_res['amount']
            cert.vat_amount = vat
            cert.withholding_amount = wht
            cert.net_payable = work + vat - wht - cert.retention_amount

    def action_load_agreement_lines(self):
        """Add one line per agreement line not yet on the certificate (draft only)."""
        for cert in self.filtered(lambda c: c.state == 'draft'):
            missing = cert.agreement_id.line_ids - cert.line_ids.agreement_line_id
            cert.line_ids = [Command.create({'agreement_line_id': line.id}) for line in missing]

    def action_submit_for_approval(self):
        self._check_construction_role(*self._submit_group_xmlids)
        for cert in self:
            if not cert.line_ids:
                raise UserError(self.env._('%(cert)s has no lines.', cert=cert.name))
            pending = self.search([('agreement_id', '=', cert.agreement_id.id), ('id', '!=', cert.id),
                                   ('state', 'in', ('submitted', 'approved_l1'))], limit=1)
            if pending:
                raise UserError(self.env._(
                    '%(other)s is already waiting for approval on this agreement.', other=pending.name))
            cert.line_ids._refresh_previous()
        return super().action_submit_for_approval()

    def action_create_bill(self):
        self.ensure_one()
        self._check_construction_role('nt_construction.group_construction_accountant')
        if self.state != 'approved':
            raise UserError(self.env._('Only approved subcontractor certificates can be billed.'))
        if self.move_id:
            raise UserError(self.env._('This certificate already has a vendor bill.'))
        company = self.company_id
        if self.retention_amount and not company.construction_retention_payable_account_id:
            raise UserError(self.env._('Configure the Retention Payable account in Construction Settings.'))
        analytic = self.project_id.account_id
        distribution = {str(analytic.id): 100.0} if analytic else False
        taxes = company.construction_purchase_tax_id | company.construction_purchase_withholding_tax_id
        work_vals = {
            'name': self.env._('%(cert)s - Work executed this period', cert=self.name),
            'quantity': 1.0, 'price_unit': self.work_amount,
            'tax_ids': [Command.set(taxes.ids)],
            'analytic_distribution': distribution,
        }
        if company.construction_subcontract_cost_account_id:
            work_vals['account_id'] = company.construction_subcontract_cost_account_id.id
        lines = [work_vals]
        if not self.currency_id.is_zero(self.retention_amount):
            lines.append({
                'name': self.env._('%(cert)s - Retention', cert=self.name),
                'quantity': 1.0, 'price_unit': -self.retention_amount,
                'account_id': company.construction_retention_payable_account_id.id,
                'tax_ids': [Command.clear()],
            })
        move = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_id.id,
            'currency_id': self.currency_id.id,
            'invoice_date': self.date,
            'ref': self.name,
            'invoice_origin': self.agreement_id.name,
            'construction_project_id': self.project_id.id,
            'construction_move_kind': 'subcontract_certificate',
            'invoice_line_ids': [Command.create(vals) for vals in lines],
        })
        self._workflow_write({'move_id': move.id})
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('Vendor Bill'),
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': move.id,
        }

    def action_view_bill(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.move_id.id,
        }


class SubcontractCertificateLine(models.Model):
    _name = 'subcontract.certificate.line'
    _inherit = ['construction.locked.line']
    _locked_parent_field = 'certificate_id'
    _description = 'Subcontractor Certificate Line'

    certificate_id = fields.Many2one('subcontract.certificate', required=True, ondelete='cascade', index=True)
    currency_id = fields.Many2one(related='certificate_id.currency_id')
    agreement_line_id = fields.Many2one(
        'subcontract.agreement.line', required=True,
        domain="[('agreement_id', '=', parent.agreement_id)]")
    boq_line_id = fields.Many2one(related='agreement_line_id.boq_line_id', store=True)
    name = fields.Char(related='agreement_line_id.name')
    quantity_agreed = fields.Float(related='agreement_line_id.quantity', string='Agreed Qty')
    unit_price = fields.Monetary(related='agreement_line_id.unit_price', groups=AMOUNT_GROUPS)
    quantity_previous = fields.Float(readonly=True, digits='Product Unit of Measure')
    quantity_total = fields.Float(string='Total Qty to Date', digits='Product Unit of Measure', default=0.0)
    quantity_this_period = fields.Float(
        string='Current Qty', compute='_compute_quantities', store=True, digits='Product Unit of Measure')
    amount_this_period = fields.Monetary(
        string='Current Amount', currency_field='currency_id', compute='_compute_quantities', store=True,
        groups=AMOUNT_GROUPS)
    amount_total = fields.Monetary(
        string='Total Amount', currency_field='currency_id', compute='_compute_quantities', store=True,
        groups=AMOUNT_GROUPS)

    _agreement_line_uniq = models.Constraint(
        'unique(certificate_id, agreement_line_id)', 'An agreement line can appear only once per certificate.')

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._refresh_previous()
        return lines

    def _refresh_previous(self):
        for line in self.filtered(lambda ln: ln.certificate_id.state == 'draft'):
            approved = self.search([
                ('agreement_line_id', '=', line.agreement_line_id.id),
                ('certificate_id.state', '=', 'approved'), ('id', '!=', line.id)])
            previous = sum(approved.mapped('quantity_this_period'))
            vals = {}
            if line.quantity_previous != previous:
                vals['quantity_previous'] = previous
            if not line.quantity_total and previous:
                vals['quantity_total'] = previous  # new line: nothing claimed this period yet
            if vals:
                line.write(vals)

    @api.depends('quantity_total', 'quantity_previous', 'agreement_line_id.unit_price')
    def _compute_quantities(self):
        for line in self:
            price = line.sudo().agreement_line_id.unit_price
            line.quantity_this_period = line.quantity_total - line.quantity_previous
            current = line.quantity_this_period * price
            total = line.quantity_total * price
            if line.currency_id:
                current, total = line.currency_id.round(current), line.currency_id.round(total)
            line.amount_this_period = current
            line.amount_total = total

    @api.constrains('quantity_total', 'quantity_previous')
    def _check_quantities(self):
        for line in self.filtered(lambda ln: ln.certificate_id.state == 'draft'):
            if float_compare(line.quantity_total, line.quantity_previous, precision_digits=4) < 0:
                raise ValidationError(self.env._(
                    '%(item)s: total to date cannot be lower than the quantity already certified.',
                    item=line.name or line.boq_line_id.display_name))
            agreed = line.quantity_agreed
            if agreed and float_compare(line.quantity_total, agreed * 1.001, precision_digits=4) > 0:
                raise ValidationError(self.env._(
                    '%(item)s: total to date (%(total).2f) exceeds the agreed quantity (%(agreed).2f).',
                    item=line.name or line.boq_line_id.display_name, total=line.quantity_total, agreed=agreed))
