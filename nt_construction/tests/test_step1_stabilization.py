from psycopg2 import IntegrityError

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, new_test_user, tagged
from odoo.tools import mute_logger


@tagged('post_install', '-at_install', 'nt_construction')
class TestStep1Stabilization(TransactionCase):
    """Regression tests for the defects found in BASELINE.md (Phase 0)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.manager = new_test_user(
            cls.env, login='nt_step1_manager',
            groups='base.group_user,project.group_project_manager,'
                   'nt_construction.group_construction_approver_l2',
        )
        # final approval must come from another approver (segregation of duties, DECISIONS Q4)
        cls.final_approver = new_test_user(
            cls.env, login='nt_step1_final_approver',
            groups='base.group_user,nt_construction.group_construction_approver_l2',
        )
        # master data is created as superuser; business documents as the manager
        cls.client = cls.env['res.partner'].create({'name': 'Step1 Client'})
        cls.subcontractor = cls.env['res.partner'].create({'name': 'Step1 Subcontractor'})
        cls.env = cls.env(user=cls.manager)

        cls.tender = cls.env['tender.tender'].create({
            'client_id': cls.client.id,
            'submission_deadline': fields.Datetime.now(),
            'awarded_value': 1000.0,
        })
        cls.chapter = cls.env['boq.line'].create({'tender_id': cls.tender.id, 'name': 'Civil Works'})
        cls.item = cls.env['boq.line'].create({
            'tender_id': cls.tender.id, 'parent_id': cls.chapter.id, 'name': 'Concrete',
            'quantity_contracted': 10.0, 'unit_price': 100.0,
        })
        cls.tender.action_submit()
        cls.tender.action_set_won()
        cls.tender.action_create_project()
        cls.project = cls.tender.project_id
        cls.project_item = cls.env['boq.line'].search(
            [('project_id', '=', cls.project.id), ('is_group', '=', False)])

    # ------------------------------------------------------------------
    # Tender -> project
    # ------------------------------------------------------------------
    def test_tender_to_project(self):
        self.assertEqual(self.tender.boq_total_contracted, 1000.0)
        self.assertEqual(self.tender.state, 'won')
        self.assertTrue(self.project.is_construction_project)
        self.assertEqual(self.project.contract_value, 1000.0)
        self.assertEqual(self.env['boq.line'].search_count([('project_id', '=', self.project.id)]), 2)
        self.assertEqual(len(self.project_item), 1)
        # as-bid BOQ is kept on the tender
        self.assertEqual(self.env['boq.line'].search_count([('tender_id', '=', self.tender.id)]), 2)

    # ------------------------------------------------------------------
    # Previously crashing computes (BASELINE §2)
    # ------------------------------------------------------------------
    def _approved_subcontract(self):
        agreement = self.env['subcontract.agreement'].create({
            'project_id': self.project.id,
            'partner_id': self.subcontractor.id,
            'line_ids': [Command.create({
                'boq_line_id': self.project_item.id, 'quantity': 5.0, 'unit_price': 50.0,
            })],
        })
        agreement.action_submit_for_approval()
        agreement.action_approve_l1()
        agreement.with_user(self.final_approver).action_approve_l2()
        return agreement

    def test_project_subcontract_computes(self):
        self.assertEqual(self.project.subcontract_agreement_count, 0)
        self.assertEqual(self.project.total_subcontracted_committed, 0.0)
        agreement = self._approved_subcontract()
        self.assertEqual(agreement.state, 'approved')
        self.assertEqual(self.project.subcontract_agreement_count, 1)
        self.assertEqual(self.project.total_subcontracted_committed, 250.0)

    def test_boq_committed_amount(self):
        self.assertEqual(self.project_item.committed_amount, 0.0)
        self._approved_subcontract()
        self.assertEqual(self.project_item.committed_amount, 250.0)

    # ------------------------------------------------------------------
    # Variation order state (BASELINE W2)
    # ------------------------------------------------------------------
    def _variation_order(self, delta_qty=2.0):
        return self.env['boq.variation.order'].create({
            'project_id': self.project.id,
            'line_ids': [Command.create({
                'boq_line_id': self.project_item.id, 'name': 'Extra concrete',
                'delta_qty': delta_qty, 'unit_price': 100.0,
            })],
        })

    def test_variation_order_reject_and_reset(self):
        vo = self._variation_order()
        vo.action_submit_for_approval()
        vo.action_reject()
        self.assertEqual(vo.state, 'rejected')
        vo.action_reset_draft()
        self.assertEqual(vo.state, 'draft')
        self.assertFalse(vo.applied)
        self.assertEqual(self.project.contract_value, 1000.0)

    def test_variation_order_approval_applies(self):
        vo = self._variation_order()
        vo.action_submit_for_approval()
        vo.action_approve_l1()
        vo.with_user(self.final_approver).action_approve_l2()
        self.assertEqual(vo.state, 'approved')
        self.assertTrue(vo.applied)
        self.assertEqual(self.project.contract_value, 1200.0)
        self.assertEqual(self.project_item.quantity_contracted, 12.0)

    # ------------------------------------------------------------------
    # Company on documents
    # ------------------------------------------------------------------
    def test_company_on_vo_and_certificate(self):
        vo = self._variation_order()
        cert = self.env['boq.payment.certificate'].create({
            'project_id': self.project.id,
            'line_ids': [Command.create({'boq_line_id': self.project_item.id, 'quantity_this_period': 1.0})],
        })
        self.assertEqual(vo.company_id, self.project.company_id)
        self.assertEqual(cert.company_id, self.project.company_id)

    # ------------------------------------------------------------------
    # Sequences (previously missing -> every record named "New")
    # ------------------------------------------------------------------
    def test_sequences_generate_distinct_names(self):
        today = fields.Date.today()
        docs = {
            'site.daily.report': [
                {'project_id': self.project.id, 'date': today},
                {'project_id': self.project.id, 'date': fields.Date.add(today, days=-1)},
            ],
            # distinct dicts: create() writes the sequence name into each vals dict
            'project.handover': [{'project_id': self.project.id} for _i in range(2)],
            'work.measurement': [{'project_id': self.project.id} for _i in range(2)],
            'subcontract.agreement': [
                {'project_id': self.project.id, 'partner_id': self.subcontractor.id} for _i in range(2)],
        }
        for model, vals_list in docs.items():
            records = self.env[model].create(vals_list)
            names = records.mapped('name')
            self.assertEqual(len(set(names)), 2, model)
            self.assertNotIn('New', names, model)

    # ------------------------------------------------------------------
    # Uniqueness constraints (BASELINE W1)
    # ------------------------------------------------------------------
    @mute_logger('odoo.sql_db')
    def test_tender_reference_unique(self):
        with self.assertRaises(IntegrityError), self.cr.savepoint():
            self.env['tender.tender'].create({'client_id': self.client.id, 'name': self.tender.name})

    @mute_logger('odoo.sql_db')
    def test_daily_report_unique_per_project_and_date(self):
        today = fields.Date.today()
        self.env['site.daily.report'].create({'project_id': self.project.id, 'date': today})
        with self.assertRaises(IntegrityError), self.cr.savepoint():
            self.env['site.daily.report'].create({'project_id': self.project.id, 'date': today})

    # ------------------------------------------------------------------
    # BOQ hierarchy (replaces deprecated _check_recursion)
    # ------------------------------------------------------------------
    def test_boq_hierarchy_cycle_rejected(self):
        # parent_store raises "Recursion Detected" (UserError); our _has_cycle
        # constraint (ValidationError, a UserError subclass) is the fallback.
        with self.assertRaises(UserError):
            self.chapter.parent_id = self.item
