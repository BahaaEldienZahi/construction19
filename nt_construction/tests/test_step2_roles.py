from lxml import etree

from odoo import Command, fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, new_test_user, tagged

ROLE = 'nt_construction.group_construction_%s'


@tagged('post_install', '-at_install', 'nt_construction')
class TestStep2Roles(TransactionCase):
    """Role matrix (DECISIONS Q2), own-project rules (Q3/S6), segregation (Q4), Q6, Q7."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        def user(login, *roles):
            return new_test_user(cls.env, login=login, groups=','.join(ROLE % r for r in roles))

        cls.te = user('nt_te', 'tender_engineer')
        cls.se = user('nt_se', 'site_engineer')
        cls.qs = user('nt_qs', 'quantity_surveyor')
        cls.pm = user('nt_pm', 'project_manager')
        cls.pm_b = user('nt_pm_b', 'project_manager')
        cls.acc = user('nt_acc', 'accountant')
        cls.l1 = user('nt_l1', 'approver_l1')
        cls.l2 = user('nt_l2', 'approver_l2')
        cls.l2_other = user('nt_l2_other', 'approver_l2')
        cls.qs_l1 = user('nt_qs_l1', 'quantity_surveyor', 'approver_l1')

        cls.client = cls.env['res.partner'].create({'name': 'Roles Client'})
        # accounting setup needed by invoicing / retention release (step 3 settings)
        Account = cls.env['account.account']
        cls.env.company.write({
            'construction_retention_account_id': Account.create(
                {'code': 'NTR1250', 'name': 'Retention Receivable', 'account_type': 'asset_current'}).id,
            'construction_advance_account_id': Account.create(
                {'code': 'NTR2150', 'name': 'Customer Advances', 'account_type': 'liability_current'}).id,
        })
        # tender -> project A as the tender engineer (conversion runs sudo inside)
        te_env = cls.env(user=cls.te)
        cls.tender = te_env['tender.tender'].create({
            'client_id': cls.client.id, 'submission_deadline': fields.Datetime.now(),
            'awarded_value': 1000.0, 'user_id': cls.pm.id,
        })
        chapter = te_env['boq.line'].create({'tender_id': cls.tender.id, 'name': 'Civil'})
        cls.tender_item = te_env['boq.line'].create({
            'tender_id': cls.tender.id, 'parent_id': chapter.id, 'name': 'Concrete',
            'quantity_contracted': 10.0, 'unit_price': 100.0,
        })
        cls.tender.action_submit()
        cls.tender.action_set_won()
        cls.tender.action_create_project()
        cls.project_a = cls.tender.project_id.with_env(cls.env)  # back to superuser for setup
        cls.project_a.construction_member_ids = [Command.set((cls.se | cls.qs).ids)]
        cls.item_a = cls.env['boq.line'].search([('project_id', '=', cls.project_a.id), ('is_group', '=', False)])

        cls.project_b = cls.env['project.project'].create({
            'name': 'Project B', 'is_construction_project': True, 'user_id': cls.pm_b.id,
            'partner_id': cls.client.id, 'company_id': cls.env.company.id,
        })
        cls.item_b = cls.env['boq.line'].create({
            'project_id': cls.project_b.id, 'name': 'Steel', 'quantity_contracted': 5.0, 'unit_price': 50.0,
        })
        cls.cert_b = cls.env['boq.payment.certificate'].create({
            'project_id': cls.project_b.id,
            'line_ids': [Command.create({'boq_line_id': cls.item_b.id, 'quantity_total': 1.0})],
        })
        cls.report_b = cls.env['site.daily.report'].create({'project_id': cls.project_b.id})

    def _cert_a(self, user=None):
        return self.env(user=user or self.qs)['boq.payment.certificate'].create({
            'project_id': self.project_a.id,
            'line_ids': [Command.create({'boq_line_id': self.item_a.id, 'quantity_total': 1.0})],
        })

    def _approved_cert_a(self):
        cert = self._cert_a()
        cert.action_submit_for_approval()
        cert.with_user(self.l1).action_approve_l1()
        cert.with_user(self.l2).action_approve_l2()
        self.assertEqual(cert.state, 'approved')
        return cert

    def _visible(self, user, records):
        return records.with_user(user).search([('id', 'in', records.ids)])

    # ------------------------------------------------------------------
    def test_tender_engineer(self):
        self.assertEqual(self.tender.state, 'won')
        self.assertTrue(self.project_a.is_construction_project)
        self.assertEqual(len(self.item_a), 1, 'BOQ copied to the project by the conversion')
        # tender BOQ only, no project documents
        self.assertFalse(self._visible(self.te, self.item_a))
        with self.assertRaises(AccessError):
            self.env(user=self.te)['boq.payment.certificate'].search([])
        with self.assertRaises(AccessError):
            self.env(user=self.te)['site.daily.report'].create({'project_id': self.project_a.id})

    def test_site_engineer(self):
        se_env = self.env(user=self.se)
        report = se_env['site.daily.report'].create({
            'project_id': self.project_a.id, 'date': fields.Date.today(),
            'progress_ids': [Command.create({'boq_line_id': self.item_a.id, 'quantity_executed': 2.0})],
        })
        self.assertEqual(report.state, 'draft')
        with self.assertRaises(UserError):
            report.action_confirm()  # the project manager confirms
        se_env['work.measurement'].create({'project_id': self.project_a.id})
        # own project only
        self.assertFalse(self._visible(self.se, self.report_b))
        self.assertFalse(self._visible(self.se, self.project_b))
        # quantities yes, prices and amounts no (Q7)
        self.assertEqual(self.item_a.with_user(self.se).read(['quantity_contracted'])[0]['quantity_contracted'], 10.0)
        for fname in ('unit_price', 'total_contracted'):
            with self.subTest(field=fname), self.assertRaises(AccessError):
                self.item_a.with_user(self.se).read([fname])
        with self.assertRaises(AccessError):
            self.project_a.with_user(self.se).read(['contract_value'])
        with self.assertRaises(AccessError):
            se_env['boq.payment.certificate'].create({'project_id': self.project_a.id})

    def test_site_engineer_views_render_without_amounts(self):
        for model in ('boq.line', 'site.daily.report', 'work.measurement', 'project.project'):
            with self.subTest(model=model):
                views = self.env[model].with_user(self.se).get_views([(False, 'list'), (False, 'form')])
                for view in views['views'].values():
                    field_names = set(etree.fromstring(view['arch']).xpath('//field/@name'))
                    hidden = {'unit_price', 'total_contracted', 'contract_value', 'total_amount_executed_today'}
                    self.assertFalse(field_names & hidden)

    def test_quantity_surveyor(self):
        cert = self._cert_a()
        cert.action_submit_for_approval()
        for action in ('action_approve_l1', 'action_reject'):
            with self.subTest(action=action), self.assertRaises(UserError):
                getattr(cert, action)()
        self.assertFalse(self._visible(self.qs, self.cert_b))
        # tender BOQ is visible to the QS (pricing), as are own-project lines
        self.assertEqual(self._visible(self.qs, self.tender_item | self.item_a | self.item_b),
                         self.tender_item | self.item_a)
        measurement = self.env(user=self.qs)['work.measurement'].create({'project_id': self.project_a.id})
        measurement.action_confirm()
        self.assertEqual(measurement.state, 'confirmed')

    def test_quantity_surveyor_cannot_invoice(self):
        cert = self._approved_cert_a()
        with self.assertRaises(UserError):
            cert.with_user(self.qs).action_create_invoice()

    def test_project_manager_sees_own_projects_only(self):
        report_a = self.env['site.daily.report'].create({'project_id': self.project_a.id})
        reports = report_a | self.report_b
        self.assertEqual(self._visible(self.pm, reports), report_a)
        self.assertEqual(self._visible(self.pm_b, reports), self.report_b)
        self.assertEqual(self.env['project.project'].with_user(self.pm).search(
            [('id', 'in', (self.project_a | self.project_b).ids)]), self.project_a)
        report_a.with_user(self.pm).action_confirm()
        self.assertEqual(report_a.state, 'confirmed')
        with self.assertRaises(AccessError):
            self.env(user=self.pm)['boq.payment.certificate'].create({'project_id': self.project_a.id})

    def test_company_wide_roles_see_all_projects(self):
        cert_a = self._cert_a()
        for user in (self.acc, self.l1, self.l2, self.qs_l1):
            with self.subTest(user=user.login):
                self.assertEqual(self._visible(user, cert_a | self.cert_b), cert_a | self.cert_b)

    def test_approver_cannot_create_certificate(self):
        with self.assertRaises(AccessError):
            self.env(user=self.l2)['boq.payment.certificate'].create({'project_id': self.project_a.id})

    def test_segregation_of_duties(self):
        cert = self._cert_a()
        cert.action_submit_for_approval()
        cert.with_user(self.l2).action_approve_l1()
        with self.assertRaises(UserError):
            cert.with_user(self.l2).action_approve_l2()
        cert.with_user(self.l2_other).action_approve_l2()
        self.assertEqual(cert.state, 'approved')

    def test_l1_cannot_give_final_approval(self):
        cert = self._cert_a()
        cert.action_submit_for_approval()
        cert.with_user(self.l1).action_approve_l1()
        with self.assertRaises(UserError):
            cert.with_user(self.l1).action_approve_l1()  # already L1-approved
        with self.assertRaises(UserError):
            cert.with_user(self.l1).action_approve_l2()

    def test_accountant_invoices_approved_certificate(self):
        cert = self._approved_cert_a()
        cert.with_user(self.acc).action_create_invoice()
        self.assertTrue(cert.move_id)
        self.assertEqual(cert.move_id.move_type, 'out_invoice')

    def test_handover_roles_and_reset_after_release(self):
        handover = self.env(user=self.pm)['project.handover'].create({
            'project_id': self.project_a.id, 'provisional_handover_date': fields.Date.today()})
        handover.action_confirm_provisional_handover()
        with self.assertRaises(UserError):
            handover.action_release_retention_stage1()  # accountant only
        handover.with_user(self.acc).action_release_retention_stage1()
        self.assertTrue(handover.retention_release_stage1_done)
        with self.assertRaises(UserError):
            handover.action_reset_draft()  # Q6
        self.assertEqual(handover.state, 'provisional')

    def test_linked_measurement_cannot_be_reset(self):
        measurement = self.env(user=self.qs)['work.measurement'].create({'project_id': self.project_a.id})
        measurement._workflow_write({'state': 'linked'})
        with self.assertRaises(UserError):
            measurement.action_reset_draft()
