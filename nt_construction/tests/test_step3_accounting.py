from odoo import Command, fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import new_test_user, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install', 'nt_construction')
class TestStep3Accounting(AccountTestInvoicingCommon):
    """Golden accounting cycle (BASELINE §3 defects, DECISIONS S7, S12-S15, A8).

    Contract 200,000: item A 100 x 1,000 + item B 50 x 2,000. Retention 5 %, advance 10 %
    (recovered at 10 % of each certificate), VAT 14 % on gross, withholding 1 % on gross.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # the invoicing test user also administers projects (passes construction role checks) and buys
        cls.env.user.sudo().group_ids = [Command.link(cls.env.ref('project.group_project_manager').id),
                                         Command.link(cls.env.ref('purchase.group_purchase_manager').id)]
        company = cls.env.company
        Account = cls.env['account.account']

        def account(code, name, account_type):
            return Account.create({'code': code, 'name': name, 'account_type': account_type})

        cls.acc_revenue = account('NT4000', 'Construction Revenue', 'income')
        cls.acc_retention = account('NT1250', 'Retention Receivable', 'asset_current')
        cls.acc_advance = account('NT2150', 'Customer Advances', 'liability_current')
        cls.acc_vat = account('NT2200', 'VAT Payable', 'liability_current')
        cls.acc_wht = account('NT1260', 'Withholding Tax Receivable', 'asset_current')
        cls.acc_sub_cost = account('NT5100', 'Subcontract Cost', 'expense')
        cls.acc_ret_payable = account('NT2160', 'Retention Payable', 'liability_current')
        cls.acc_vat_in = account('NT1270', 'VAT Receivable', 'asset_current')

        def tax(name, amount, use, tax_account):
            t = cls.env['account.tax'].create({
                'name': name, 'amount_type': 'percent', 'amount': amount, 'type_tax_use': use})
            (t.invoice_repartition_line_ids | t.refund_repartition_line_ids).filtered(
                lambda r: r.repartition_type == 'tax').account_id = tax_account
            return t

        cls.vat = tax('NT VAT 14%', 14.0, 'sale', cls.acc_vat)
        cls.wht = tax('NT WHT 1%', -1.0, 'sale', cls.acc_wht)
        cls.vat_in = tax('NT VAT 14% (purchase)', 14.0, 'purchase', cls.acc_vat_in)
        company.write({
            'construction_revenue_account_id': cls.acc_revenue.id,
            'construction_retention_account_id': cls.acc_retention.id,
            'construction_advance_account_id': cls.acc_advance.id,
            'construction_sale_tax_id': cls.vat.id,
            'construction_withholding_tax_id': cls.wht.id,
            'construction_advance_tax_id': cls.vat.id,
            'construction_escalation_vat': True,
            'construction_subcontract_cost_account_id': cls.acc_sub_cost.id,
            'construction_retention_payable_account_id': cls.acc_ret_payable.id,
            'construction_purchase_tax_id': cls.vat_in.id,
        })
        cls.approver_l1 = new_test_user(cls.env, login='nt_s3_l1', groups='nt_construction.group_construction_approver_l1')
        cls.approver_l2 = new_test_user(cls.env, login='nt_s3_l2', groups='nt_construction.group_construction_approver_l2')
        cls.client = cls.env['res.partner'].create({'name': 'S3 Client'})
        cls.subcontractor = cls.env['res.partner'].create({'name': 'S3 Subcontractor'})
        cls.project = cls._project()
        cls.item_a, cls.item_b = cls._items(cls.project)

    @classmethod
    def _project(cls, **vals):
        return cls.env['project.project'].create({
            'name': 'S3 Tower', 'is_construction_project': True, 'partner_id': cls.client.id,
            'company_id': cls.env.company.id, 'construction_currency_id': cls.env.company.currency_id.id,
            'contract_value': 200_000.0, 'retention_percentage': 5.0,
            'advance_payment_percentage': 10.0, 'advance_recovery_percentage': 10.0,
            **vals,
        })

    @classmethod
    def _items(cls, project):
        chapter = cls.env['boq.line'].create({'project_id': project.id, 'name': 'Civil'})
        return cls.env['boq.line'].create([
            {'project_id': project.id, 'parent_id': chapter.id, 'code': 'A', 'name': 'Concrete',
             'quantity_contracted': 100.0, 'unit_price': 1_000.0},
            {'project_id': project.id, 'parent_id': chapter.id, 'code': 'B', 'name': 'Steel',
             'quantity_contracted': 50.0, 'unit_price': 2_000.0},
        ])

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _certificate(self, quantities, project=None):
        project = project or self.project
        items = self.env['boq.line'].search([('project_id', '=', project.id), ('is_group', '=', False)], order='code')
        return self.env['boq.payment.certificate'].create({
            'project_id': project.id,
            'line_ids': [Command.create({'boq_line_id': item.id, 'quantity_total': qty})
                         for item, qty in zip(items, quantities) if qty is not None],
        })

    def _approve(self, cert):
        cert.action_submit_for_approval()
        cert.with_user(self.approver_l1).action_approve_l1()
        cert.with_user(self.approver_l2).action_approve_l2()
        self.assertEqual(cert.state, 'approved')
        return cert

    def _invoice(self, cert):
        cert.action_create_invoice()
        cert.move_id.action_post()
        return cert.move_id

    def _advance(self, project=None):
        project = project or self.project
        action = project.action_create_advance_invoice()
        move = self.env['account.move'].browse(action['res_id'])
        move.action_post()
        return move

    def _balances(self, move):
        balances = {}
        for line in move.line_ids:
            balances[line.account_id] = balances.get(line.account_id, 0.0) + line.balance
        return balances

    def _receivable(self, move):
        return sum(move.line_ids.filtered(lambda line: line.account_id.account_type == 'asset_receivable')
                   .mapped('balance'))

    # ------------------------------------------------------------------
    # Advance invoice (S14)
    # ------------------------------------------------------------------
    def test_advance_invoice_entries(self):
        move = self._advance()
        balances = self._balances(move)
        self.assertAlmostEqual(balances[self.acc_advance], -20_000.0)
        self.assertAlmostEqual(balances[self.acc_vat], -2_800.0)
        self.assertAlmostEqual(self._receivable(move), 22_800.0)
        self.assertEqual(move.construction_move_kind, 'advance')
        self.assertAlmostEqual(self.project.advance_invoiced_amount, 20_000.0)
        with self.assertRaises(UserError):
            self.project.action_create_advance_invoice()  # already fully invoiced

    # ------------------------------------------------------------------
    # Client certificate invoice (S12, S13, S14)
    # ------------------------------------------------------------------
    def test_certificate_invoice_entries(self):
        self._advance()
        cert = self._approve(self._certificate([30.0, 10.0]))
        self.assertAlmostEqual(cert.work_amount, 50_000.0)
        self.assertAlmostEqual(cert.retention_amount, 2_500.0)
        self.assertAlmostEqual(cert.advance_recovery_amount, 5_000.0)
        self.assertAlmostEqual(cert.vat_amount, 6_300.0)        # 7,000 on gross - 700 on recovery
        self.assertAlmostEqual(cert.withholding_amount, 500.0)
        self.assertAlmostEqual(cert.net_payable, 48_300.0)
        move = self._invoice(cert)
        balances = self._balances(move)
        self.assertAlmostEqual(balances[self.acc_revenue], -50_000.0)
        self.assertAlmostEqual(balances[self.acc_retention], 2_500.0)
        self.assertAlmostEqual(balances[self.acc_advance], 5_000.0)
        self.assertAlmostEqual(balances[self.acc_vat], -6_300.0)
        self.assertAlmostEqual(balances[self.acc_wht], 500.0)
        self.assertAlmostEqual(self._receivable(move), 48_300.0)
        self.assertAlmostEqual(sum(move.line_ids.mapped('balance')), 0.0)
        self.assertEqual(move.construction_project_id, self.project)
        self.assertAlmostEqual(self.project.advance_recovered_amount, 5_000.0)
        self.assertAlmostEqual(self.project.advance_remaining_amount, 15_000.0)
        self.assertAlmostEqual(self.project.retention_held_amount, 2_500.0)

    def test_previous_current_total(self):
        cert1 = self._approve(self._certificate([30.0, 10.0]))
        cert2 = self._certificate([60.0, 10.0])
        line_a, line_b = cert2.line_ids.sorted(lambda line: line.boq_line_id.code)
        self.assertEqual((line_a.quantity_previous, line_a.quantity_this_period, line_a.quantity_total), (30.0, 30.0, 60.0))
        self.assertEqual((line_b.quantity_previous, line_b.quantity_this_period), (10.0, 0.0))
        self.assertAlmostEqual(cert2.work_amount_previous, 50_000.0)
        self.assertAlmostEqual(cert2.work_amount, 30_000.0)
        self.assertAlmostEqual(cert2.work_amount_total, 80_000.0)
        self._approve(cert2)
        self.assertEqual(self.item_a.quantity_certified_cumulative, 60.0)
        self.assertAlmostEqual(self.item_a.amount_certified_cumulative, 60_000.0)
        self.assertEqual(cert1.line_ids.filtered(lambda line: line.boq_line_id == self.item_a).quantity_previous, 0.0,
                         'previous quantities are frozen once submitted')

    def test_cumulative_quantity_rules(self):
        self._approve(self._certificate([30.0, None]))
        with self.assertRaises(ValidationError):
            self._certificate([20.0, None])  # lower than certified
        with self.assertRaises(ValidationError):
            self._certificate([101.0, None])  # above contracted
        self._certificate([40.0, None]).action_submit_for_approval()
        with self.assertRaises(UserError):
            self._certificate([50.0, None]).action_submit_for_approval()  # one in approval at a time

    # ------------------------------------------------------------------
    # Escalation (P1, P2, P5) and S7
    # ------------------------------------------------------------------
    def _escalation_project(self, **vals):
        project = self._project(
            name='S3 Escalation', escalation_enabled=True, escalation_fixed_portion=0.15, escalation_threshold=5.0,
            escalation_component_ids=[
                Command.create({'name': 'Steel', 'coefficient': 0.5, 'base_index': 100.0}),
                Command.create({'name': 'Cement', 'coefficient': 0.35, 'base_index': 200.0}),
            ], **vals)
        self._items(project)
        return project

    def _set_indices(self, cert, steel, cement):
        for line in cert.escalation_line_ids:
            line.current_index = steel if line.name == 'Steel' else cement

    def test_escalation_formula_and_threshold(self):
        project = self._escalation_project()
        cert = self._certificate([30.0, 10.0], project)
        self.assertEqual(len(cert.escalation_line_ids), 2)
        self._set_indices(cert, 120.0, 210.0)       # 0.15 + 0.5*1.2 + 0.35*1.05 - 1 = 0.1175
        self.assertAlmostEqual(cert.escalation_factor, 0.1175, places=6)
        self.assertAlmostEqual(cert.escalation_amount, 5_875.0)
        self.assertAlmostEqual(cert.gross_amount, 55_875.0)
        self.assertAlmostEqual(cert.retention_amount, 2_793.75)  # P5: retention on escalation
        self._set_indices(cert, 104.0, 200.0)       # +2 %, inside the 5 % threshold
        self.assertAlmostEqual(cert.escalation_amount, 0.0)
        project.escalation_deduct_threshold = True
        self._set_indices(cert, 120.0, 210.0)
        self.assertAlmostEqual(cert.escalation_factor, 0.0675, places=6)

    def test_escalation_weights_must_total_one(self):
        with self.assertRaises(ValidationError):
            self._project(name='Bad', escalation_enabled=True, escalation_fixed_portion=0.2, escalation_component_ids=[
                Command.create({'name': 'Steel', 'coefficient': 0.5, 'base_index': 100.0})])

    def test_certified_equals_invoiced_excl_vat_incl_escalation(self):
        """DECISIONS S7: same basis - both excluding VAT, both including escalation."""
        project = self._escalation_project()
        cert1 = self._certificate([30.0, 10.0], project)
        self._set_indices(cert1, 120.0, 210.0)
        self._approve(cert1)
        self._invoice(cert1)
        cert2 = self._certificate([60.0, 20.0], project)
        self._set_indices(cert2, 110.0, 200.0)
        self._approve(cert2)
        self._invoice(cert2)
        figures = project._get_construction_financials()[project.id]
        expected = cert1.work_amount + cert1.escalation_amount + cert2.work_amount + cert2.escalation_amount
        self.assertGreater(cert1.escalation_amount, 0.0)
        self.assertAlmostEqual(figures['certified'], expected)
        self.assertAlmostEqual(figures['invoiced'], figures['certified'])
        self.assertAlmostEqual(figures['certified_pct'], round(expected / 200_000.0 * 100, 2))

    def test_collected(self):
        move = self._invoice(self._approve(self._certificate([30.0, 10.0])))
        self.env['account.payment.register'].with_context(
            active_model='account.move', active_ids=move.ids).create({})._create_payments()
        figures = self.project._get_construction_financials()[self.project.id]
        self.assertAlmostEqual(figures['collected'], move.amount_total)
        self.assertAlmostEqual(figures['collected_pct'], 100.0)

    # ------------------------------------------------------------------
    # Executed vs certified (A8): no double counting
    # ------------------------------------------------------------------
    def test_executed_from_measurements_only(self):
        report = self.env['site.daily.report'].create({
            'project_id': self.project.id, 'date': fields.Date.today(),
            'progress_ids': [Command.create({'boq_line_id': self.item_a.id, 'quantity_executed': 3.0})]})
        report.action_confirm()
        self.assertEqual(self.item_a.quantity_reported_cumulative, 3.0)
        self.assertEqual(self.item_a.quantity_executed_cumulative, 0.0)
        measurement = self.env['work.measurement'].create({
            'project_id': self.project.id,
            'progress_ids': [Command.create({'boq_line_id': self.item_a.id, 'quantity_executed': 3.0})]})
        measurement.action_confirm()
        self.assertEqual(self.item_a.quantity_executed_cumulative, 3.0)
        self._approve(self._certificate([3.0, None]))
        self.assertEqual(self.item_a.quantity_executed_cumulative, 3.0, 'certificate approval must not add execution')
        self.assertEqual(self.item_a.quantity_certified_cumulative, 3.0)
        figures = self.project._get_construction_financials()[self.project.id]
        self.assertAlmostEqual(figures['executed'], 3_000.0)
        self.assertAlmostEqual(figures['executed_not_certified'], 0.0)

    # ------------------------------------------------------------------
    # Retention release (2 stages) and subcontractor bill
    # ------------------------------------------------------------------
    def test_retention_release_entries(self):
        self._invoice(self._approve(self._certificate([30.0, 10.0])))
        self._invoice(self._approve(self._certificate([60.0, 10.0])))
        self.assertAlmostEqual(self.project.retention_held_amount, 4_000.0)
        handover = self.env['project.handover'].create({
            'project_id': self.project.id, 'provisional_handover_date': fields.Date.today()})
        handover.action_confirm_provisional_handover()
        handover.action_release_retention_stage1()
        move = handover.retention_release_stage1_move_id
        move.action_post()
        balances = self._balances(move)
        self.assertAlmostEqual(balances[self.acc_retention], -2_000.0)
        self.assertAlmostEqual(self._receivable(move), 2_000.0)
        self.assertFalse(move.line_ids.filtered(lambda line: line.tax_line_id), 'no VAT on retention release')
        self.assertAlmostEqual(self.project.retention_held_amount, 2_000.0)
        handover.action_final_handover()
        handover.action_release_retention_stage2()
        self.assertAlmostEqual(handover.retention_release_stage2_amount, 2_000.0)
        self.assertAlmostEqual(self.project.retention_held_amount, 0.0)

    def test_subcontractor_certificate_bill(self):
        agreement = self.env['subcontract.agreement'].create({
            'project_id': self.project.id, 'partner_id': self.subcontractor.id, 'retention_percentage': 5.0,
            'line_ids': [Command.create({'boq_line_id': self.item_b.id, 'quantity': 20.0, 'unit_price': 500.0})]})
        self._approve(agreement)
        cert = self.env['subcontract.certificate'].create({'agreement_id': agreement.id})
        cert.action_load_agreement_lines()
        cert.line_ids.quantity_total = 8.0
        self.assertAlmostEqual(cert.work_amount, 4_000.0)
        self.assertAlmostEqual(cert.net_payable, 4_360.0)
        self._approve(cert)
        cert.action_create_bill()
        bill = cert.move_id
        bill.action_post()
        balances = self._balances(bill)
        self.assertAlmostEqual(balances[self.acc_sub_cost], 4_000.0)
        self.assertAlmostEqual(balances[self.acc_vat_in], 560.0)
        self.assertAlmostEqual(balances[self.acc_ret_payable], -200.0)
        payable = sum(bill.line_ids.filtered(lambda line: line.account_id.account_type == 'liability_payable')
                      .mapped('balance'))
        self.assertAlmostEqual(payable, -4_360.0)
        cost_line = bill.invoice_line_ids.filtered(lambda line: line.account_id == self.acc_sub_cost)
        if self.project.account_id:
            self.assertEqual(cost_line.analytic_distribution, {str(self.project.account_id.id): 100.0})
        cert2 = self.env['subcontract.certificate'].create({'agreement_id': agreement.id})
        cert2.action_load_agreement_lines()
        self.assertEqual(cert2.line_ids.quantity_previous, 8.0)

    # ------------------------------------------------------------------
    # Multi-currency
    # ------------------------------------------------------------------
    def test_foreign_currency_contract(self):
        code = 'EUR' if self.env.company.currency_id.name != 'EUR' else 'GBP'
        fx = self.setup_other_currency(code, rates=[('2000-01-01', 0.5)])  # 1 company unit = 0.5 foreign
        self.assertNotEqual(fx, self.env.company.currency_id)
        project = self._project(name='S3 FX', construction_currency_id=fx.id)
        item_a, _item_b = self._items(project)
        self.assertEqual(item_a.currency_id, fx)
        cert = self._approve(self._certificate([10.0, None], project))
        move = self._invoice(cert)
        self.assertEqual(move.currency_id, fx)
        self.assertAlmostEqual(move.amount_untaxed, 10_000.0 - 500.0)      # work - retention, in USD
        revenue = move.line_ids.filtered(lambda line: line.account_id == self.acc_revenue)
        self.assertAlmostEqual(revenue.amount_currency, -10_000.0)
        self.assertAlmostEqual(revenue.balance, -20_000.0)                  # company currency at rate 0.5
        po = self.env['purchase.order'].create({
            'partner_id': self.subcontractor.id, 'project_id': project.id,
            'order_line': [Command.create({
                'product_id': self.product_a.id, 'product_qty': 1.0, 'price_unit': 2_000.0,
                'boq_line_id': item_a.id})],
        })
        po.button_confirm()
        self.assertAlmostEqual(item_a.committed_amount, 1_000.0, msg='PO in company currency converted to USD')
