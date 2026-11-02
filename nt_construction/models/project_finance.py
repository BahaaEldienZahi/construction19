from odoo import Command, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare, float_is_zero

AMOUNT_GROUPS = 'nt_construction.group_construction_see_amounts,project.group_project_manager'


class ConstructionEscalationComponent(models.Model):
    """One index of the escalation formula (DECISIONS P1): factor = a + sum(b_i * I_i / I0_i) - 1,
    where a is the project's fixed portion and a + sum(b_i) = 1. No coefficient is hardcoded."""
    _name = 'construction.escalation.component'
    _description = 'Price Escalation Index Component'
    _order = 'project_id, sequence, id'

    project_id = fields.Many2one('project.project', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(default=10)
    name = fields.Char(string='Index', required=True, help='e.g. Steel, Cement, Labour, Fuel.')
    coefficient = fields.Float(string='Weight (b)', digits=(16, 4), required=True)
    base_index = fields.Float(string='Base Index (I0)', digits=(16, 4), required=True,
                              help='Index value at the project base date.')

    @api.constrains('base_index', 'coefficient')
    def _check_values(self):
        for comp in self:
            if float_compare(comp.base_index, 0.0, precision_digits=6) <= 0:
                raise ValidationError(self.env._('The base index of %(name)s must be positive.', name=comp.name))
            if float_compare(comp.coefficient, 0.0, precision_digits=6) < 0:
                raise ValidationError(self.env._('The weight of %(name)s cannot be negative.', name=comp.name))


class ProjectProject(models.Model):  # pylint: disable=consider-merging-classes-inherited
    """Billing terms, escalation, advance and the shared financial figures (step 3); kept apart
    from project_project.py (contract / BOQ / visibility) on purpose."""
    _inherit = 'project.project'

    # ---- billing terms
    advance_recovery_percentage = fields.Float(
        string='Advance Recovery %', default=0.0,
        help='Share of each certificate\'s work value deducted to recover the advance, until it is fully '
             'recovered. Usually equal to the advance %.')
    retention_on_escalation = fields.Boolean(
        string='Retention on Escalation', default=True,
        help='PROVISIONAL (DECISIONS P5): retention also applies to the escalation amount.')
    construction_withholding_tax_id = fields.Many2one(
        'account.tax', string='Withholding Tax', check_company=True,
        domain=[('type_tax_use', '=', 'sale')],
        help='Overrides the company default withholding tax for this project\'s certificates (S13).')

    # ---- escalation (فروق أسعار) — configurable formula (P1)
    escalation_enabled = fields.Boolean(string='Price Escalation')
    escalation_base_date = fields.Date(help='Date of the base indices (usually the tender date).')
    escalation_fixed_portion = fields.Float(
        string='Fixed Portion (a)', digits=(16, 4),
        help='Non-adjustable share of the contract price; fixed portion + sum of weights must equal 1.')
    escalation_threshold = fields.Float(
        string='Threshold %', help='No escalation while the absolute change stays within this percentage.')
    escalation_deduct_threshold = fields.Boolean(
        string='Deduct Threshold', help='Pay only the change beyond the threshold.')
    escalation_component_ids = fields.One2many('construction.escalation.component', 'project_id')

    # ---- advance payment
    construction_move_ids = fields.One2many('account.move', 'construction_project_id')
    advance_invoiced_amount = fields.Monetary(
        currency_field='construction_currency_id', compute='_compute_advance', store=True,
        groups=AMOUNT_GROUPS, help='Untaxed amount of posted advance invoices.')
    advance_recovered_amount = fields.Monetary(
        currency_field='construction_currency_id', compute='_compute_advance', store=True,
        groups=AMOUNT_GROUPS, help='Advance recovered in approved certificates.')
    advance_remaining_amount = fields.Monetary(
        currency_field='construction_currency_id', compute='_compute_advance', store=True,
        groups=AMOUNT_GROUPS)
    certificate_ids = fields.One2many('boq.payment.certificate', 'project_id')

    @api.depends('construction_move_ids.state', 'construction_move_ids.amount_untaxed',
                 'construction_move_ids.construction_move_kind',
                 'certificate_ids.state', 'certificate_ids.advance_recovery_amount')
    def _compute_advance(self):
        for project in self:
            advances = project.construction_move_ids.filtered(
                lambda m: m.construction_move_kind == 'advance' and m.state == 'posted')
            invoiced = sum(advances.mapped(lambda m: m.amount_untaxed * (-1 if m.move_type == 'out_refund' else 1)))
            recovered = sum(project.certificate_ids.filtered(
                lambda c: c.state == 'approved').mapped('advance_recovery_amount'))
            project.advance_invoiced_amount = invoiced
            project.advance_recovered_amount = recovered
            project.advance_remaining_amount = invoiced - recovered

    @api.constrains('escalation_enabled', 'escalation_fixed_portion', 'escalation_component_ids')
    def _check_escalation_weights(self):
        for project in self.filtered('escalation_enabled'):
            if not project.escalation_component_ids:
                continue
            total = project.escalation_fixed_portion + sum(project.escalation_component_ids.mapped('coefficient'))
            if float_compare(total, 1.0, precision_digits=4) != 0:
                raise ValidationError(self.env._(
                    'Price escalation of %(project)s: fixed portion + index weights = %(total).4f; it must be 1.',
                    project=project.display_name, total=total))

    # ------------------------------------------------------------------
    # Advance invoice (DECISIONS S14)
    # ------------------------------------------------------------------
    def action_create_advance_invoice(self):
        self.ensure_one()
        self.env['construction.workflow.guard']._check_construction_role(
            'nt_construction.group_construction_accountant')
        company = self.company_id
        if not company.construction_advance_account_id:
            raise UserError(self.env._('Configure the Customer Advances account in Construction Settings.'))
        if not self.partner_id:
            raise UserError(self.env._('Set the client on project %(project)s first.', project=self.display_name))
        already = sum(self.construction_move_ids.filtered(
            lambda m: m.construction_move_kind == 'advance' and m.state != 'cancel').mapped('amount_untaxed'))
        amount = self.construction_currency_id.round(
            self.sudo().contract_value * self.advance_payment_percentage / 100.0 - already)
        if float_compare(amount, 0.0, precision_digits=2) <= 0:
            raise UserError(self.env._('The advance of %(project)s is already invoiced.', project=self.display_name))
        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'currency_id': self.construction_currency_id.id,
            'invoice_origin': self.display_name,
            'construction_project_id': self.id,
            'construction_move_kind': 'advance',
            'invoice_line_ids': [Command.create({
                'name': self.env._('Advance payment %(pct).2f%% - %(project)s',
                                   pct=self.advance_payment_percentage, project=self.display_name),
                'quantity': 1.0,
                'price_unit': amount,
                'account_id': company.construction_advance_account_id.id,
                'tax_ids': [Command.set(company.construction_advance_tax_id.ids)],
            })],
        })
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('Advance Invoice'),
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': move.id,
        }

    # ------------------------------------------------------------------
    # Shared financial figures (UX_SPEC 3.0, DECISIONS S7, U7, U8)
    # ------------------------------------------------------------------
    def _get_construction_financials(self):
        """Executed / Certified / Invoiced / Collected per project, in the contract currency,
        excluding VAT and including escalation. One definition for every screen."""
        result = {}
        for project in self.sudo():
            certs = project.certificate_ids.filtered(lambda c: c.state == 'approved')
            leaves = self.env['boq.line'].sudo().search([('project_id', '=', project.id), ('is_group', '=', False)])
            executed = sum(leaves.mapped('amount_executed_cumulative'))
            certified = sum(certs.mapped('work_amount')) + sum(certs.mapped('escalation_amount'))
            invoiced = collected = receivable_total = 0.0
            excluded_accounts = (project.company_id.construction_retention_account_id
                                 | project.company_id.construction_advance_account_id)
            moves = certs.move_id.filtered(lambda m: m.state == 'posted')
            refunds = self.env['account.move'].sudo().search(
                [('reversed_entry_id', 'in', moves.ids), ('state', '=', 'posted')])
            for move in moves | refunds:
                sign = -1 if move.move_type == 'out_refund' else 1
                invoiced += sign * sum(move.invoice_line_ids.filtered(
                    lambda line: line.account_id not in excluded_accounts).mapped('price_subtotal'))
                receivable_total += sign * move.amount_total
                collected += sign * (move.amount_total - move.amount_residual)
            contract = project.contract_value

            def pct(value, base):
                return round(value / base * 100.0, 2) if not float_is_zero(base, precision_digits=2) else 0.0

            result[project.id] = {
                'contract': contract,
                'executed': executed,
                'certified': certified,
                'invoiced': invoiced,
                'collected': collected,
                'executed_not_certified': max(0.0, executed - certified),
                'executed_pct': pct(executed, contract),
                'certified_pct': pct(certified, contract),
                'invoiced_pct': pct(invoiced, contract),
                'collected_pct': pct(collected, receivable_total),
            }
        return result
