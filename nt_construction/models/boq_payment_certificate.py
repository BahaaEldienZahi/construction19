from odoo import Command, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare, float_is_zero

AMOUNT_GROUPS = 'nt_construction.group_construction_see_amounts,project.group_project_manager'


class BoqPaymentCertificate(models.Model):
    """Client payment certificate: previous / current / total per BOQ item, escalation,
    retention, advance recovery, VAT and withholding tax -> customer invoice (DECISIONS S12-S15)."""
    _name = 'boq.payment.certificate'
    _description = 'BOQ Payment Certificate (Progress Billing)'
    _check_company_auto = True
    _inherit = ['construction.approval.mixin', 'mail.thread', 'mail.activity.mixin']

    _workflow_guarded_fields = (
        'state', 'approver_l1_id', 'approval_l1_date', 'approver_l2_id', 'approval_l2_date', 'move_id',
    )
    _submit_group_xmlids = ('nt_construction.group_construction_quantity_surveyor',)
    _order = 'date desc, id desc'

    name = fields.Char(default=lambda self: self.env._('New'), readonly=True, copy=False)
    project_id = fields.Many2one(
        'project.project', required=True,
        domain=[('is_construction_project', '=', True)], tracking=True,
        check_company=True,
    )
    partner_id = fields.Many2one(related='project_id.partner_id', string='Client')
    date = fields.Date(default=fields.Date.context_today, required=True)
    period_from = fields.Date()
    period_to = fields.Date()
    company_id = fields.Many2one(related='project_id.company_id', store=True, index=True)
    currency_id = fields.Many2one(related='project_id.construction_currency_id', readonly=True)

    line_ids = fields.One2many('boq.payment.certificate.line', 'certificate_id', string='Lines', copy=True)
    escalation_line_ids = fields.One2many(
        'boq.payment.certificate.escalation', 'certificate_id', string='Escalation Indices')

    # ---- work value (previous / current / total)
    work_amount_previous = fields.Monetary(
        string='Previous Work', currency_field='currency_id', compute='_compute_work', store=True,
        groups=AMOUNT_GROUPS)
    work_amount = fields.Monetary(
        string='Current Work', currency_field='currency_id', compute='_compute_work', store=True,
        groups=AMOUNT_GROUPS)
    work_amount_total = fields.Monetary(
        string='Total Work to Date', currency_field='currency_id', compute='_compute_work', store=True,
        groups=AMOUNT_GROUPS)

    # ---- escalation: formula fully configured on the project (DECISIONS P1, no constants here)
    escalation_factor = fields.Float(compute='_compute_escalation', store=True, digits=(16, 6))
    escalation_amount = fields.Monetary(
        currency_field='currency_id', compute='_compute_escalation', store=True, groups=AMOUNT_GROUPS)

    # ---- deductions and taxes
    gross_amount = fields.Monetary(
        string='Gross (Work + Escalation)', currency_field='currency_id',
        compute='_compute_amounts', store=True, groups=AMOUNT_GROUPS,
        help='Current work plus escalation: the VAT and withholding base (S12, S13).')
    retention_percentage = fields.Float(related='project_id.retention_percentage', readonly=True)
    retention_amount = fields.Monetary(
        string='Retention', currency_field='currency_id', compute='_compute_amounts', store=True,
        groups=AMOUNT_GROUPS)
    advance_recovery_amount = fields.Monetary(
        string='Advance Recovery', currency_field='currency_id', groups=AMOUNT_GROUPS,
        help='Proposed from the project recovery % (capped by the remaining advance) until edited by hand; '
             'frozen at submission.')
    advance_recovery_manual = fields.Boolean(copy=False)
    vat_amount = fields.Monetary(
        string='VAT', currency_field='currency_id', compute='_compute_amounts', store=True,
        groups=AMOUNT_GROUPS)
    withholding_amount = fields.Monetary(
        string='Withholding Tax', currency_field='currency_id', compute='_compute_amounts', store=True,
        groups=AMOUNT_GROUPS)
    net_payable = fields.Monetary(
        currency_field='currency_id', compute='_compute_amounts', store=True, groups=AMOUNT_GROUPS,
        help='What the client pays: gross + VAT - withholding - retention - advance recovery (and its VAT).')

    move_id = fields.Many2one('account.move', string='Customer Invoice', readonly=True, copy=False,
                              check_company=True)
    move_state = fields.Selection(related='move_id.state', string='Invoice Status')
    reversal_move_ids = fields.One2many(related='move_id.reversal_move_ids', string='Credit Notes')
    is_final = fields.Boolean(
        string='Final Certificate', copy=False, tracking=True,
        help='Closing account of the project (F13): recovers the whole remaining advance, whatever the '
             'recovery %, and no certificate can be submitted after it.')
    measurement_ids = fields.One2many('work.measurement', 'payment_certificate_id', string='Measurements')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', self.env._('New')) == self.env._('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('boq.payment.certificate') or self.env._('New')
        certificates = super().create(vals_list)
        certificates._sync_escalation_lines()
        certificates._refresh_draft_values()
        return certificates

    def _sync_escalation_lines(self):
        """One escalation line per project index component; the QS enters the current index."""
        for cert in self.filtered(lambda c: c.project_id.escalation_enabled and c.state == 'draft'):
            missing = cert.project_id.escalation_component_ids - cert.escalation_line_ids.component_id
            if missing:
                cert.escalation_line_ids = [Command.create({'component_id': comp.id}) for comp in missing]

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends('line_ids.amount_previous', 'line_ids.amount_this_period', 'line_ids.amount_total')
    def _compute_work(self):
        for cert in self:
            cert.work_amount_previous = sum(cert.line_ids.mapped('amount_previous'))
            cert.work_amount = sum(cert.line_ids.mapped('amount_this_period'))
            cert.work_amount_total = sum(cert.line_ids.mapped('amount_total'))

    @api.depends('work_amount', 'escalation_line_ids.current_index', 'project_id.escalation_enabled',
                 'project_id.escalation_fixed_portion', 'project_id.escalation_threshold',
                 'project_id.escalation_deduct_threshold')
    def _compute_escalation(self):
        for cert in self:
            project = cert.project_id
            factor = 0.0
            lines = cert.escalation_line_ids
            if project.escalation_enabled and lines and not any(
                    float_is_zero(line.current_index, precision_digits=6) for line in lines):
                raw = project.escalation_fixed_portion + sum(
                    line.coefficient * line.current_index / line.base_index for line in lines) - 1.0
                threshold = project.escalation_threshold / 100.0
                if abs(raw) <= threshold:
                    factor = 0.0
                elif project.escalation_deduct_threshold:
                    factor = raw - threshold if raw > 0 else raw + threshold
                else:
                    factor = raw
            cert.escalation_factor = factor
            cert.escalation_amount = cert.currency_id.round(cert.work_amount * factor) if cert.currency_id else 0.0

    def write(self, vals):
        if 'advance_recovery_amount' in vals and not self.env.context.get('nt_refresh'):
            vals = dict(vals, advance_recovery_manual=True)
        res = super().write(vals)
        if not self.env.context.get('nt_refresh') and {'line_ids', 'project_id', 'is_final'} & set(vals):
            self._refresh_draft_values()
        return res

    def _refresh_draft_values(self):
        """Draft certificates follow the project: previous quantities and prices from the BOQ,
        proposed advance recovery. Called on edit and once more at submission, then frozen."""
        drafts = self.filtered(lambda c: c.state == 'draft').with_context(nt_refresh=True)
        drafts.line_ids._refresh_from_boq()
        for cert in drafts.filtered(lambda c: not c.advance_recovery_manual):
            project = cert.project_id
            remaining = project.advance_invoiced_amount - project.advance_recovered_amount
            if cert.is_final:
                proposed = max(0.0, remaining)  # final certificate: recover everything left (F13)
            else:
                proposed = max(0.0, min(cert.work_amount * project.advance_recovery_percentage / 100.0, remaining))
            proposed = cert.currency_id.round(proposed) if cert.currency_id else proposed
            if cert.advance_recovery_amount != proposed:
                cert.advance_recovery_amount = proposed

    @api.depends('work_amount', 'escalation_amount', 'retention_percentage', 'advance_recovery_amount',
                 'project_id.retention_on_escalation', 'project_id.construction_withholding_tax_id',
                 'company_id.construction_sale_tax_id', 'company_id.construction_withholding_tax_id',
                 'company_id.construction_advance_tax_id', 'company_id.construction_escalation_vat')
    def _compute_amounts(self):
        for cert in self:
            gross = cert.work_amount + cert.escalation_amount
            retention_base = gross if cert.project_id.retention_on_escalation else cert.work_amount
            cert.gross_amount = gross
            retention = retention_base * cert.retention_percentage / 100.0
            cert.retention_amount = cert.currency_id.round(retention) if cert.currency_id else retention
            vat = wht = 0.0
            for vals in cert._get_invoice_line_vals():
                taxes = vals['nt_taxes']
                if not taxes:
                    continue
                res = taxes.compute_all(vals['price_unit'], currency=cert.currency_id, partner=cert.partner_id)
                for tax_res in res['taxes']:
                    if vals['nt_kind'] == 'advance_recovery' or tax_res['amount'] >= 0:
                        vat += tax_res['amount']  # recovery VAT is negative (S14)
                    else:
                        wht -= tax_res['amount']
            cert.vat_amount = vat
            cert.withholding_amount = wht
            cert.net_payable = gross + vat - wht - cert.retention_amount - cert.advance_recovery_amount

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------
    def action_submit_for_approval(self):
        self._check_construction_role(*self._submit_group_xmlids)
        for cert in self:
            if not cert.line_ids:
                raise UserError(self.env._('%(cert)s has no lines.', cert=cert.name))
            pending = self.search([('project_id', '=', cert.project_id.id), ('id', '!=', cert.id),
                                   ('state', 'in', ('submitted', 'approved_l1'))], limit=1)
            if pending:
                # previous quantities are frozen at submission: one certificate in approval at a time
                raise UserError(self.env._(
                    '%(other)s is already waiting for approval on this project. Approve or reject it '
                    'before submitting %(cert)s.', other=pending.name, cert=cert.name))
            final = self.search([('project_id', '=', cert.project_id.id), ('id', '!=', cert.id),
                                 ('is_final', '=', True), ('state', '=', 'approved')], limit=1)
            if final:
                raise UserError(self.env._(
                    '%(final)s is the final certificate of this project: no certificate can follow it.',
                    final=final.name))
            cert._refresh_draft_values()
            if cert.project_id.escalation_enabled and any(
                    float_is_zero(line.current_index, precision_digits=6) for line in cert.escalation_line_ids):
                raise UserError(self.env._('Enter the current value of every escalation index first.'))
        return super().action_submit_for_approval()

    def _on_final_approval(self):
        """Certified quantities are read from approved certificate lines (boq.line computes);
        nothing is written to execution progress any more (no double counting, DECISIONS A8)."""
        self.measurement_ids.filtered(lambda m: m.state == 'confirmed')._workflow_write({'state': 'linked'})

    def action_cancel(self):
        """Cancel a certificate. An approved one (F12) is cancelled only if it is the latest approved
        certificate of its project, nothing is in approval after it and no retention was released;
        its posted invoice is reversed by a credit note (unpaid invoices only), a draft one is cancelled."""
        approved = self.filtered(lambda c: c.state == 'approved')
        if approved:
            self._check_construction_role('nt_construction.group_construction_accountant')
        for cert in approved:
            project = cert.project_id
            others = self.search([('project_id', '=', project.id), ('id', '!=', cert.id),
                                  ('state', 'in', ('submitted', 'approved_l1', 'approved'))])
            later = others.filtered(lambda c: c.state != 'approved' or (
                c.approval_l2_date, c.id) > (cert.approval_l2_date, cert.id))
            if later:
                raise UserError(self.env._(
                    '%(cert)s cannot be cancelled: %(later)s was issued after it. Cancel the later '
                    'certificates first.', cert=cert.name, later=', '.join(later.mapped('name'))))
            if any(project.sudo().handover_ids.mapped(
                    lambda h: h.retention_release_stage1_done or h.retention_release_stage2_done)):
                raise UserError(self.env._(
                    '%(cert)s cannot be cancelled: retention was already released on this project.', cert=cert.name))
            move = cert.move_id
            if move.state == 'posted':
                if move.payment_state not in ('not_paid', 'reversed'):
                    raise UserError(self.env._(
                        'Invoice %(move)s of %(cert)s already has payments. Unreconcile them first, then '
                        'cancel the certificate.', move=move.name, cert=cert.name))
                if move.payment_state != 'reversed':
                    move._reverse_moves([{
                        'ref': self.env._('Cancellation of certificate %(cert)s', cert=cert.name),
                        'invoice_date': fields.Date.context_today(self),
                        'construction_project_id': project.id,
                        'construction_move_kind': 'certificate',
                    }], cancel=True)
            elif move.state == 'draft':
                move.button_cancel()
            cert.measurement_ids.sudo()._workflow_write({'state': 'confirmed', 'payment_certificate_id': False})
            cert.message_post(body=self.env._('Certificate cancelled; invoice %(move)s reversed.',
                                              move=move.display_name or '-'))
        return super().action_cancel()

    def _check_cancel_allowed(self):
        """Approved certificates are reversible (action_cancel above checks the conditions)."""
        return

    def action_reset_draft(self):
        if any(cert.state == 'cancelled' and cert.move_id for cert in self):
            raise UserError(self.env._(
                'A cancelled certificate that was invoiced cannot be reopened. Issue a new certificate.'))
        return super().action_reset_draft()

    def action_view_invoice(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('Customer Invoice'),
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.move_id.id,
        }

    # ------------------------------------------------------------------
    # Invoice
    # ------------------------------------------------------------------
    def _get_withholding_tax(self):
        return self.project_id.construction_withholding_tax_id or self.company_id.construction_withholding_tax_id

    def _get_invoice_line_vals(self):
        """Invoice lines (with helper keys nt_kind / nt_taxes); also used to preview VAT and
        withholding on the certificate."""
        self.ensure_one()
        company = self.company_id
        tax_model = self.env['account.tax']
        vat = company.construction_sale_tax_id
        wht = self._get_withholding_tax()
        esc_vat = vat if company.construction_escalation_vat else tax_model
        analytic = self.project_id.account_id
        distribution = {str(analytic.id): 100.0} if analytic else False
        lines = []

        def add(kind, name, amount, taxes, account):
            if not self.currency_id or self.currency_id.is_zero(amount):
                return
            vals = {
                'nt_kind': kind, 'nt_taxes': taxes,
                'name': name, 'quantity': 1.0, 'price_unit': amount,
                'tax_ids': [Command.set(taxes.ids)],
                'analytic_distribution': distribution,
            }
            if account:
                vals['account_id'] = account.id
            lines.append(vals)

        revenue = company.construction_revenue_account_id
        add('work', self.env._('%(cert)s - Work executed this period', cert=self.name),
            self.work_amount, vat | wht, revenue)
        add('escalation', self.env._('%(cert)s - Price escalation', cert=self.name),
            self.escalation_amount, esc_vat | wht, revenue)
        add('retention', self.env._('%(cert)s - Retention', cert=self.name),
            -self.retention_amount, tax_model, company.construction_retention_account_id)
        add('advance_recovery', self.env._('%(cert)s - Advance recovery', cert=self.name),
            -self.advance_recovery_amount, company.construction_advance_tax_id,
            company.construction_advance_account_id)
        return lines

    def _check_accounting_setup(self):
        company = self.company_id
        missing = []
        if self.retention_amount and not company.construction_retention_account_id:
            missing.append(company._fields['construction_retention_account_id'].string)
        if self.advance_recovery_amount and not company.construction_advance_account_id:
            missing.append(company._fields['construction_advance_account_id'].string)
        if missing:
            raise UserError(self.env._('Configure in Construction Settings: %(fields)s.', fields=', '.join(missing)))

    def action_create_invoice(self):
        self.ensure_one()
        self._check_construction_role('nt_construction.group_construction_accountant')
        if self.state != 'approved':
            raise UserError(self.env._('Only approved certificates can be invoiced.'))
        if self.move_id:
            raise UserError(self.env._('This certificate already has a linked invoice.'))
        if float_compare(self.net_payable, 0.0, precision_digits=2) <= 0:
            raise UserError(self.env._('Net payable amount must be positive to create an invoice.'))
        self._check_accounting_setup()
        lines = [{k: v for k, v in vals.items() if not k.startswith('nt_')} for vals in self._get_invoice_line_vals()]
        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.project_id.partner_id.id,
            'currency_id': self.currency_id.id,
            'invoice_date': self.date,
            'invoice_origin': self.name,
            'construction_project_id': self.project_id.id,
            'construction_move_kind': 'certificate',
            'invoice_line_ids': [Command.create(vals) for vals in lines],
        })
        self._workflow_write({'move_id': move.id})
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('Customer Invoice'),
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': move.id,
        }


class BoqPaymentCertificateLine(models.Model):
    _name = 'boq.payment.certificate.line'
    _inherit = ['construction.locked.line']
    _locked_parent_field = 'certificate_id'
    _description = 'BOQ Payment Certificate Line'
    _order = 'certificate_id, id'

    certificate_id = fields.Many2one(
        'boq.payment.certificate', required=True, ondelete='cascade', index=True,
    )
    project_id = fields.Many2one(related='certificate_id.project_id', store=True)
    currency_id = fields.Many2one(related='certificate_id.currency_id', readonly=True)

    boq_line_id = fields.Many2one(
        'boq.line', string='BOQ Item', required=True,
        domain="[('project_id', '=', project_id), ('is_group', '=', False)]",
    )
    code = fields.Char(related='boq_line_id.code')
    uom_id = fields.Many2one(related='boq_line_id.uom_id')
    # price snapshot refreshed in draft: later VO price changes do not alter a submitted certificate
    unit_price = fields.Monetary(currency_field='currency_id', readonly=True, groups=AMOUNT_GROUPS)
    quantity_contracted = fields.Float(
        related='boq_line_id.quantity_contracted', string='Contracted Qty', readonly=True)

    quantity_previous = fields.Float(
        string='Previous Qty', readonly=True, digits='Product Unit of Measure',
        help='Certified in earlier approved certificates. Frozen once this certificate is submitted.')
    quantity_total = fields.Float(
        string='Total Qty to Date', digits='Product Unit of Measure', default=0.0,
        help='Cumulative quantity to date, entered by the QS (DECISIONS S15).')
    quantity_this_period = fields.Float(
        string='Current Qty', compute='_compute_quantity_this_period', store=True,
        digits='Product Unit of Measure')

    amount_previous = fields.Monetary(
        currency_field='currency_id', compute='_compute_amounts', store=True, groups=AMOUNT_GROUPS)
    amount_this_period = fields.Monetary(
        string='Current Amount', currency_field='currency_id', compute='_compute_amounts', store=True,
        groups=AMOUNT_GROUPS)
    amount_total = fields.Monetary(
        string='Total Amount', currency_field='currency_id', compute='_compute_amounts', store=True,
        groups=AMOUNT_GROUPS)

    _boq_line_uniq = models.Constraint(
        'unique(certificate_id, boq_line_id)',
        'A BOQ item can appear only once per certificate.',
    )

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._refresh_from_boq()
        return lines

    def write(self, vals):
        res = super().write(vals)
        if 'boq_line_id' in vals:
            self._refresh_from_boq()
        return res

    def _refresh_from_boq(self):
        for line in self.filtered(lambda ln: ln.certificate_id.state == 'draft'):
            boq = line.boq_line_id.sudo()  # unit price is hidden from some roles; snapshot is server-side
            vals = {'quantity_previous': boq.quantity_certified_cumulative, 'unit_price': boq.unit_price}
            if not line.quantity_total and vals['quantity_previous']:
                vals['quantity_total'] = vals['quantity_previous']  # new line: nothing claimed this period yet
            if any(line[k] != v for k, v in vals.items()):
                line.write(vals)

    @api.depends('quantity_total', 'quantity_previous')
    def _compute_quantity_this_period(self):
        for line in self:
            line.quantity_this_period = line.quantity_total - line.quantity_previous

    @api.depends('quantity_previous', 'quantity_this_period', 'unit_price')
    def _compute_amounts(self):
        for line in self:
            currency = line.currency_id
            previous = line.quantity_previous * line.unit_price
            current = line.quantity_this_period * line.unit_price
            if currency:
                previous, current = currency.round(previous), currency.round(current)
            line.amount_previous = previous
            line.amount_this_period = current
            line.amount_total = previous + current

    @api.constrains('quantity_total', 'quantity_previous', 'boq_line_id')
    def _check_quantities(self):
        for line in self:
            if line.certificate_id.state != 'draft':
                continue
            if float_compare(line.quantity_total, line.quantity_previous, precision_digits=4) < 0:
                raise ValidationError(self.env._(
                    '%(item)s: the total quantity to date (%(total).2f) cannot be lower than the quantity '
                    'already certified (%(previous).2f).',
                    item=line.boq_line_id.display_name, total=line.quantity_total, previous=line.quantity_previous))
            contracted = line.boq_line_id.quantity_contracted
            if contracted and float_compare(line.quantity_total, contracted * 1.001, precision_digits=4) > 0:
                raise ValidationError(self.env._(
                    '%(item)s: the total quantity to date (%(total).2f) exceeds the contracted quantity '
                    '(%(contracted).2f). Issue a variation order first.',
                    item=line.boq_line_id.display_name, total=line.quantity_total, contracted=contracted))


class BoqPaymentCertificateEscalation(models.Model):
    _name = 'boq.payment.certificate.escalation'
    _inherit = ['construction.locked.line']
    _locked_parent_field = 'certificate_id'
    _description = 'Certificate Escalation Index'
    _order = 'certificate_id, sequence, id'

    certificate_id = fields.Many2one('boq.payment.certificate', required=True, ondelete='cascade', index=True)
    component_id = fields.Many2one('construction.escalation.component', required=True, ondelete='restrict')
    sequence = fields.Integer(related='component_id.sequence', store=True)
    name = fields.Char(related='component_id.name')
    coefficient = fields.Float(related='component_id.coefficient', digits=(16, 4))
    base_index = fields.Float(related='component_id.base_index', digits=(16, 4))
    current_index = fields.Float(digits=(16, 4), help='Index value for this certificate period.')
