from odoo import Command, fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install', 'nt_construction')
class TestStep2WorkflowGuard(TransactionCase):
    """Approval bypass (BASELINE §4) and multi-company record rules."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        groups = 'base.group_user,project.group_project_manager'
        cls.approver = new_test_user(
            cls.env, login='nt_s2_approver', groups=groups + ',nt_construction.group_construction_approver_l2')
        cls.user = new_test_user(cls.env, login='nt_s2_user', groups=groups)  # no approval rights
        cls.final_approver = new_test_user(
            cls.env, login='nt_s2_final_approver', groups='base.group_user,nt_construction.group_construction_approver_l2')
        cls.client = cls.env['res.partner'].create({'name': 'S2 Client'})
        cls.subcontractor = cls.env['res.partner'].create({'name': 'S2 Subcontractor'})

        env = cls.env(user=cls.approver)
        cls.tender = env['tender.tender'].create({
            'client_id': cls.client.id, 'submission_deadline': fields.Datetime.now(), 'awarded_value': 1000.0,
        })
        chapter = env['boq.line'].create({'tender_id': cls.tender.id, 'name': 'Civil'})
        env['boq.line'].create({
            'tender_id': cls.tender.id, 'parent_id': chapter.id, 'name': 'Concrete',
            'quantity_contracted': 10.0, 'unit_price': 100.0,
        })
        cls.tender.action_submit()
        cls.tender.action_set_won()
        cls.tender.action_create_project()
        cls.project = cls.tender.project_id
        cls.item = env['boq.line'].search([('project_id', '=', cls.project.id), ('is_group', '=', False)])

    def _certificate(self, user=None):
        env = self.env(user=user or self.approver)
        return env['boq.payment.certificate'].create({
            'project_id': self.project.id,
            'line_ids': [Command.create({'boq_line_id': self.item.id, 'quantity_this_period': 1.0})],
        })

    def _approved_certificate(self):
        cert = self._certificate()
        cert.action_submit_for_approval()
        cert.action_approve_l1()
        cert.with_user(self.final_approver).action_approve_l2()
        self.assertEqual(cert.state, 'approved')
        return cert

    # ------------------------------------------------------------------
    # Guarded workflow fields: only the buttons may change them
    # ------------------------------------------------------------------
    def test_direct_state_write_refused(self):
        cert = self._certificate(self.user)
        for vals in ({'state': 'approved'}, {'state': 'submitted'},
                     {'approver_l2_id': self.user.id}, {'approval_l2_date': fields.Datetime.now()}):
            with self.subTest(vals=vals), self.assertRaises(AccessError):
                cert.write(vals)
        self.assertEqual(cert.state, 'draft')

    def test_create_in_approved_state_refused(self):
        with self.assertRaises(AccessError):
            self.env(user=self.user)['boq.payment.certificate'].create({
                'project_id': self.project.id, 'state': 'approved'})
        with self.assertRaises(AccessError):
            self.env(user=self.user)['boq.variation.order'].create({
                'project_id': self.project.id, 'state': 'approved', 'applied': True})

    def test_client_context_cannot_bypass_guard(self):
        # a JSON-RPC client can send any context key; it must not unlock the guard
        cert = self._certificate(self.user)
        with self.assertRaises(AccessError):
            cert.with_context(construction_workflow=True).write({'state': 'approved'})

    def test_other_workflow_models_guarded(self):
        env = self.env(user=self.approver)
        report = env['site.daily.report'].create({'project_id': self.project.id, 'date': fields.Date.today()})
        measurement = env['work.measurement'].create({'project_id': self.project.id})
        handover = env['project.handover'].create({'project_id': self.project.id})
        cases = [
            (self.tender, {'state': 'draft'}),
            (self.tender, {'project_id': False}),
            (report, {'state': 'confirmed'}),
            (measurement, {'state': 'linked'}),
            (handover, {'state': 'closed'}),
            (handover, {'retention_release_stage1_done': True}),
        ]
        for record, vals in cases:
            with self.subTest(model=record._name, vals=vals), self.assertRaises(AccessError):
                record.write(vals)
        # the buttons still work
        report.action_confirm()
        measurement.action_confirm()
        self.assertEqual((report.state, measurement.state), ('confirmed', 'confirmed'))

    def test_invoice_link_guarded(self):
        cert = self._approved_certificate()
        move = self.env['account.move'].create({'move_type': 'out_invoice', 'partner_id': self.client.id})
        with self.assertRaises(AccessError):
            cert.with_user(self.approver).write({'move_id': move.id})

    # ------------------------------------------------------------------
    # Approved documents are frozen
    # ------------------------------------------------------------------
    def test_approved_certificate_is_frozen(self):
        cert = self._approved_certificate()
        line = cert.line_ids
        with self.assertRaises(UserError):
            cert.write({'date': fields.Date.add(cert.date, days=1)})
        with self.assertRaises(UserError):
            line.write({'quantity_this_period': 5.0})
        with self.assertRaises(UserError):
            self.env['boq.payment.certificate.line'].create({
                'certificate_id': cert.id, 'boq_line_id': self.item.id, 'quantity_this_period': 1.0})
        with self.assertRaises(UserError):
            line.unlink()
        with self.assertRaises(UserError):
            cert.unlink()
        self.assertEqual(line.quantity_this_period, 1.0)

    def test_submitted_document_is_frozen_until_rejected(self):
        cert = self._certificate()
        cert.action_submit_for_approval()
        with self.assertRaises(UserError):
            cert.line_ids.write({'quantity_this_period': 3.0})
        cert.action_reject()
        cert.action_reset_draft()
        cert.line_ids.write({'quantity_this_period': 3.0})
        self.assertEqual(cert.line_ids.quantity_this_period, 3.0)

    def test_approved_document_cannot_be_reset(self):
        cert = self._approved_certificate()
        with self.assertRaises(UserError):
            cert.action_reset_draft()
        self.assertEqual(cert.state, 'approved')

    def test_variation_order_lines_frozen_after_approval(self):
        vo = self.env(user=self.approver)['boq.variation.order'].create({
            'project_id': self.project.id,
            'line_ids': [Command.create({
                'boq_line_id': self.item.id, 'name': 'Extra', 'delta_qty': 2.0, 'unit_price': 100.0})],
        })
        vo.action_submit_for_approval()
        vo.action_approve_l1()
        vo.with_user(self.final_approver).action_approve_l2()
        self.assertTrue(vo.applied)
        self.assertEqual(self.project.contract_value, 1200.0)
        with self.assertRaises(UserError):
            vo.line_ids.write({'delta_qty': 50.0})
        with self.assertRaises(UserError):
            vo.unlink()

    # ------------------------------------------------------------------
    # Only approvers act on approvals
    # ------------------------------------------------------------------
    def test_non_approver_cannot_approve_or_reject(self):
        cert = self._certificate(self.user)
        cert.action_submit_for_approval()
        cert_as_user = cert.with_user(self.user)
        for action in ('action_approve_l1', 'action_approve_l2', 'action_reject'):
            with self.subTest(action=action), self.assertRaises(UserError):
                getattr(cert_as_user, action)()
        self.assertEqual(cert.state, 'submitted')

    # ------------------------------------------------------------------
    # Multi-company
    # ------------------------------------------------------------------
    def test_other_company_user_cannot_see_documents(self):
        company_b = self.env['res.company'].create({'name': 'S2 Company B'})
        user_b = new_test_user(
            self.env, login='nt_s2_company_b', company_id=company_b.id, company_ids=[Command.set(company_b.ids)],
            groups='base.group_user,project.group_project_manager')
        cert = self._certificate()
        for record in (self.tender, self.item, cert, cert.line_ids):
            with self.subTest(model=record._name):
                self.assertFalse(record.with_user(user_b).search([('id', '=', record.id)]))
                with self.assertRaises(AccessError):
                    record.with_user(user_b).read(['display_name'])
