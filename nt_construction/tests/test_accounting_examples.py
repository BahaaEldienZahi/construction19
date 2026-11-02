from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import new_test_user, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install', 'nt_construction')
class TestAccountingExamples(AccountTestInvoicingCommon):
    """Every number of ACCOUNTING_EXAMPLES.md, asserted as journal entries (account code -> debit, credit).

    Company currency EGP. Contract 10,000,000 EGP: item A concrete 5,000 m3 x 1,200 + item B steel
    100 t x 40,000. Retention 5 % (also on escalation, P5), advance 10 % recovered pro-rata (10 % of
    each certificate's work), VAT 14 % on work and escalation (S12, P2), client withholding 1 % (S13).
    Escalation: fixed 0.15, steel 0.50 (base 100), cement 0.35 (base 200), threshold 5 %.
    """

    @classmethod
    def setup_independent_company(cls, **kwargs):
        egp = cls.env.ref('base.EGP')
        egp.sudo().active = True
        return super().setup_independent_company(currency_id=egp.id, **kwargs)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.sudo().group_ids = [Command.link(cls.env.ref('project.group_project_manager').id),
                                         Command.link(cls.env.ref('purchase.group_purchase_manager').id)]
        company = cls.env.company
        assert company.currency_id.name == 'EGP'

        def account(code, name, account_type, **vals):
            return cls.env['account.account'].create(
                {'code': code, 'name': name, 'account_type': account_type, **vals})

        cls.acc = {
            '1121': account('1121', 'Clients', 'asset_receivable', reconcile=True),
            '1125': account('1125', 'Retention Receivable', 'asset_current'),
            '1126': account('1126', 'Withholding Tax Receivable', 'asset_current'),
            '1127': account('1127', 'VAT Input', 'asset_current'),
            '2111': account('2111', 'Subcontractors', 'liability_payable', reconcile=True),
            '2121': account('2121', 'Customer Advances', 'liability_current'),
            '2125': account('2125', 'Retention Payable', 'liability_current'),
            '2131': account('2131', 'VAT Output', 'liability_current'),
            '2132': account('2132', 'Withholding Tax Payable', 'liability_current'),
            '4101': account('4101', 'Construction Revenue', 'income'),
            '5101': account('5101', 'Subcontract Cost', 'expense'),
        }

        def tax(name, amount, use, code):
            t = cls.env['account.tax'].create(
                {'name': name, 'amount_type': 'percent', 'amount': amount, 'type_tax_use': use})
            (t.invoice_repartition_line_ids | t.refund_repartition_line_ids).filtered(
                lambda r: r.repartition_type == 'tax').account_id = cls.acc[code]
            return t

        vat = tax('VAT 14%', 14.0, 'sale', '2131')
        company.write({
            'construction_revenue_account_id': cls.acc['4101'].id,
            'construction_retention_account_id': cls.acc['1125'].id,
            'construction_advance_account_id': cls.acc['2121'].id,
            'construction_sale_tax_id': vat.id,
            'construction_withholding_tax_id': tax('WHT 1%', -1.0, 'sale', '1126').id,
            'construction_advance_tax_id': vat.id,
            'construction_escalation_vat': True,
            'construction_subcontract_cost_account_id': cls.acc['5101'].id,
            'construction_retention_payable_account_id': cls.acc['2125'].id,
            'construction_purchase_tax_id': tax('VAT 14% (purchase)', 14.0, 'purchase', '1127').id,
            'construction_purchase_withholding_tax_id': tax('WHT 1% (purchase)', -1.0, 'purchase', '2132').id,
        })
        cls.approver_l1 = new_test_user(cls.env, login='nt_ex_l1', groups='nt_construction.group_construction_approver_l1')
        cls.approver_l2 = new_test_user(cls.env, login='nt_ex_l2', groups='nt_construction.group_construction_approver_l2')
        cls.client = cls.env['res.partner'].create({
            'name': 'Example Client', 'property_account_receivable_id': cls.acc['1121'].id})
        cls.subcontractor = cls.env['res.partner'].create({
            'name': 'Example Steel Subcontractor', 'property_account_payable_id': cls.acc['2111'].id})
        cls.project = cls.env['project.project'].create({
            'name': 'Example 10M Tower', 'is_construction_project': True, 'partner_id': cls.client.id,
            'company_id': company.id, 'construction_currency_id': company.currency_id.id,
            'contract_value': 10_000_000.0, 'retention_percentage': 5.0,
            'advance_payment_percentage': 10.0, 'advance_recovery_percentage': 10.0,
            'escalation_enabled': True, 'escalation_fixed_portion': 0.15, 'escalation_threshold': 5.0,
            'escalation_component_ids': [
                Command.create({'name': 'Steel', 'coefficient': 0.5, 'base_index': 100.0}),
                Command.create({'name': 'Cement', 'coefficient': 0.35, 'base_index': 200.0}),
            ],
        })
        chapter = cls.env['boq.line'].create({'project_id': cls.project.id, 'name': 'Structure'})
        cls.item_a, cls.item_b = cls.env['boq.line'].create([
            {'project_id': cls.project.id, 'parent_id': chapter.id, 'code': 'A', 'name': 'Concrete',
             'quantity_contracted': 5_000.0, 'unit_price': 1_200.0},
            {'project_id': cls.project.id, 'parent_id': chapter.id, 'code': 'B', 'name': 'Steel',
             'quantity_contracted': 100.0, 'unit_price': 40_000.0},
        ])

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _entry(self, move):
        """{account code: (debit, credit)} of a posted move, lines on the same account netted."""
        self.assertEqual(move.state, 'posted')
        net = {}
        for line in move.line_ids:
            net[line.account_id.code] = net.get(line.account_id.code, 0.0) + line.balance
        self.assertAlmostEqual(sum(net.values()), 0.0)
        return {code: (round(max(b, 0.0), 2), round(max(-b, 0.0), 2)) for code, b in net.items()}

    def _certificate(self, qty_a, qty_b, steel, cement, **vals):
        cert = self.env['boq.payment.certificate'].create({
            'project_id': self.project.id, **vals,
            'line_ids': [Command.create({'boq_line_id': self.item_a.id, 'quantity_total': qty_a}),
                         Command.create({'boq_line_id': self.item_b.id, 'quantity_total': qty_b})],
        })
        for line in cert.escalation_line_ids:
            line.current_index = steel if line.name == 'Steel' else cement
        cert.action_submit_for_approval()
        cert.with_user(self.approver_l1).action_approve_l1()
        cert.with_user(self.approver_l2).action_approve_l2()
        cert.action_create_invoice()
        cert.move_id.action_post()
        return cert

    def _advance(self):
        move = self.env['account.move'].browse(self.project.action_create_advance_invoice()['res_id'])
        move.action_post()
        return move

    def _cert1(self):
        return self._certificate(1_500.0, 30.0, 100.0, 200.0)           # indices at base: no escalation

    def _cert2(self):
        return self._certificate(3_000.0, 55.0, 110.0, 206.0)           # factor 0.0605

    def _final(self):
        return self._certificate(4_950.0, 100.0, 110.0, 206.0, is_final=True)

    def _cancel_cert2(self, cert2):
        cert2.action_cancel()
        return cert2.move_id.reversal_move_ids

    # ------------------------------------------------------------------
    # a. advance payment invoice
    # ------------------------------------------------------------------
    def test_a_advance_invoice(self):
        move = self._advance()
        self.assertEqual(self._entry(move), {
            '1121': (1_140_000.0, 0.0),
            '2121': (0.0, 1_000_000.0),
            '2131': (0.0, 140_000.0),
        })
        self.assertAlmostEqual(self.project.advance_remaining_amount, 1_000_000.0)

    # ------------------------------------------------------------------
    # b. certificate 1 (current period, escalation within the threshold)
    # ------------------------------------------------------------------
    def test_b_certificate_1(self):
        self._advance()
        cert = self._cert1()
        self.assertAlmostEqual(cert.work_amount, 3_000_000.0)
        self.assertAlmostEqual(cert.escalation_amount, 0.0)
        self.assertAlmostEqual(cert.net_payable, 2_898_000.0)
        self.assertEqual(self._entry(cert.move_id), {
            '1121': (2_898_000.0, 0.0),
            '1125': (150_000.0, 0.0),
            '1126': (30_000.0, 0.0),
            '2121': (300_000.0, 0.0),
            '2131': (0.0, 378_000.0),       # 420,000 on work - 42,000 on the recovery
            '4101': (0.0, 3_000_000.0),
        })

    # ------------------------------------------------------------------
    # c. certificate 2: previous / current / total
    # ------------------------------------------------------------------
    def test_c_certificate_2_cumulative(self):
        self._advance()
        self._cert1()
        cert = self._cert2()
        line_a, line_b = cert.line_ids.sorted(lambda line: line.boq_line_id.code)
        self.assertEqual((line_a.quantity_previous, line_a.quantity_this_period, line_a.quantity_total),
                         (1_500.0, 1_500.0, 3_000.0))
        self.assertEqual((line_b.quantity_previous, line_b.quantity_this_period, line_b.quantity_total),
                         (30.0, 25.0, 55.0))
        self.assertEqual((cert.work_amount_previous, cert.work_amount, cert.work_amount_total),
                         (3_000_000.0, 2_800_000.0, 5_800_000.0))
        self.assertAlmostEqual(cert.advance_recovery_amount, 280_000.0)
        self.assertAlmostEqual(self.project.advance_remaining_amount, 420_000.0)
        self.assertAlmostEqual(self.project.retention_held_amount, 298_470.0)

    # ------------------------------------------------------------------
    # d. escalation on certificate 2 (journal entry of certificate 2)
    # ------------------------------------------------------------------
    def test_d_certificate_2_escalation(self):
        self._advance()
        self._cert1()
        cert = self._cert2()
        self.assertAlmostEqual(cert.escalation_factor, 0.0605, places=6)
        self.assertAlmostEqual(cert.escalation_amount, 169_400.0)
        self.assertAlmostEqual(cert.gross_amount, 2_969_400.0)
        self.assertAlmostEqual(cert.retention_amount, 148_470.0)
        self.assertAlmostEqual(cert.net_payable, 2_887_752.0)
        self.assertEqual(self._entry(cert.move_id), {
            '1121': (2_887_752.0, 0.0),
            '1125': (148_470.0, 0.0),
            '1126': (29_694.0, 0.0),
            '2121': (280_000.0, 0.0),
            '2131': (0.0, 376_516.0),       # 392,000 + 23,716 - 39,200
            '4101': (0.0, 2_969_400.0),     # 2,800,000 work + 169,400 escalation
        })
        figures = self.project._get_construction_financials()[self.project.id]
        self.assertAlmostEqual(figures['certified'], 5_969_400.0)
        self.assertAlmostEqual(figures['invoiced'], figures['certified'])

    # ------------------------------------------------------------------
    # e. subcontractor certificate -> vendor bill with retention
    # ------------------------------------------------------------------
    def test_e_subcontractor_bill(self):
        agreement = self.env['subcontract.agreement'].create({
            'project_id': self.project.id, 'partner_id': self.subcontractor.id, 'retention_percentage': 5.0,
            'line_ids': [Command.create({'boq_line_id': self.item_b.id, 'quantity': 100.0, 'unit_price': 30_000.0})]})
        agreement.action_submit_for_approval()
        agreement.with_user(self.approver_l1).action_approve_l1()
        agreement.with_user(self.approver_l2).action_approve_l2()
        cert = self.env['subcontract.certificate'].create({'agreement_id': agreement.id})
        cert.action_load_agreement_lines()
        cert.line_ids.quantity_total = 30.0
        cert.action_submit_for_approval()
        cert.with_user(self.approver_l1).action_approve_l1()
        cert.with_user(self.approver_l2).action_approve_l2()
        cert.action_create_bill()
        cert.move_id.action_post()
        self.assertAlmostEqual(cert.net_payable, 972_000.0)
        self.assertEqual(self._entry(cert.move_id), {
            '5101': (900_000.0, 0.0),
            '1127': (126_000.0, 0.0),
            '2132': (0.0, 9_000.0),
            '2125': (0.0, 45_000.0),
            '2111': (0.0, 972_000.0),
        })

    # ------------------------------------------------------------------
    # g. cancelling certificate 2 after its invoice is posted
    # ------------------------------------------------------------------
    def test_g_cancel_certificate_2(self):
        self._advance()
        self._cert1()
        cert2 = self._cert2()
        refund = self._cancel_cert2(cert2)
        self.assertEqual(cert2.state, 'cancelled')
        self.assertEqual(len(refund), 1)
        self.assertEqual(refund.move_type, 'out_refund')
        self.assertEqual(self._entry(refund), {
            '1121': (0.0, 2_887_752.0),
            '1125': (0.0, 148_470.0),
            '1126': (0.0, 29_694.0),
            '2121': (0.0, 280_000.0),
            '2131': (376_516.0, 0.0),
            '4101': (2_969_400.0, 0.0),
        })
        self.assertEqual(cert2.move_id.payment_state, 'reversed')
        # the project is back to the position after certificate 1
        self.assertEqual(self.item_a.quantity_certified_cumulative, 1_500.0)
        self.assertAlmostEqual(self.project.advance_remaining_amount, 700_000.0)
        self.assertAlmostEqual(self.project.retention_held_amount, 150_000.0)
        figures = self.project._get_construction_financials()[self.project.id]
        self.assertAlmostEqual(figures['certified'], 3_000_000.0)
        self.assertAlmostEqual(figures['invoiced'], 3_000_000.0)
        with self.assertRaises(UserError):
            cert2.action_reset_draft()   # invoiced and cancelled: issue a new certificate

    def test_g_cancel_rules(self):
        self._advance()
        cert1 = self._cert1()
        cert2 = self._cert2()
        with self.assertRaises(UserError):
            cert1.action_cancel()        # certificate 2 was issued after it
        self.env['account.payment.register'].with_context(
            active_model='account.move', active_ids=cert2.move_id.ids).create({})._create_payments()
        with self.assertRaises(UserError):
            cert2.action_cancel()        # paid invoice: unreconcile first

    # ------------------------------------------------------------------
    # h. final certificate (after certificate 2 was cancelled)
    # ------------------------------------------------------------------
    def test_h_final_certificate(self):
        self._advance()
        self._cert1()
        self._cancel_cert2(self._cert2())
        final = self._final()
        self.assertEqual((final.work_amount_previous, final.work_amount, final.work_amount_total),
                         (3_000_000.0, 6_940_000.0, 9_940_000.0))
        self.assertAlmostEqual(final.escalation_amount, 419_870.0)
        self.assertAlmostEqual(final.retention_amount, 367_993.5)
        self.assertAlmostEqual(final.advance_recovery_amount, 700_000.0)    # pro-rata would be 694,000
        self.assertAlmostEqual(final.net_payable, 7_150_659.6)
        self.assertEqual(self._entry(final.move_id), {
            '1121': (7_150_659.6, 0.0),
            '1125': (367_993.5, 0.0),
            '1126': (73_598.7, 0.0),
            '2121': (700_000.0, 0.0),
            '2131': (0.0, 932_381.8),       # 971,600 + 58,781.80 - 98,000
            '4101': (0.0, 7_359_870.0),
        })
        self.assertAlmostEqual(self.project.advance_remaining_amount, 0.0)
        self.assertAlmostEqual(self.project.retention_held_amount, 517_993.5)
        with self.assertRaises(UserError):
            self.env['boq.payment.certificate'].create({
                'project_id': self.project.id,
                'line_ids': [Command.create({'boq_line_id': self.item_a.id, 'quantity_total': 4_960.0})],
            }).action_submit_for_approval()   # nothing after the final certificate

    # ------------------------------------------------------------------
    # f. retention release, stage 1 and stage 2 (after the final certificate)
    # ------------------------------------------------------------------
    def test_f_retention_release(self):
        self._advance()
        self._cert1()
        self._cancel_cert2(self._cert2())
        self._final()
        handover = self.env['project.handover'].create({
            'project_id': self.project.id, 'provisional_handover_date': fields.Date.today()})
        handover.action_confirm_provisional_handover()
        handover.action_release_retention_stage1()
        stage1 = handover.retention_release_stage1_move_id
        stage1.action_post()
        self.assertEqual(self._entry(stage1), {
            '1121': (258_996.75, 0.0),
            '1125': (0.0, 258_996.75),
        })
        handover.action_final_handover()
        handover.action_release_retention_stage2()
        stage2 = handover.retention_release_stage2_move_id
        stage2.action_post()
        self.assertEqual(self._entry(stage2), {
            '1121': (258_996.75, 0.0),
            '1125': (0.0, 258_996.75),
        })
        self.assertAlmostEqual(self.project.retention_held_amount, 0.0)
