import ast
import itertools

from lxml import etree

from odoo.tests import TransactionCase, new_test_user, tagged
from odoo.tools.safe_eval import safe_eval

ROLES = ('tender_engineer', 'site_engineer', 'quantity_surveyor', 'project_manager',
         'accountant', 'approver_l1', 'approver_l2')

# documents that follow the form standard (UX Phase A); others join after step 3
STANDARD_FORMS = ('tender.tender', 'site.daily.report', 'subcontract.agreement', 'project.handover')


@tagged('post_install', '-at_install', 'nt_construction')
class TestUxFormStandard(TransactionCase):
    """UX_SPEC §2.1: for every state, at most one highlighted (btn-primary) header button."""

    def _header_buttons(self, model):
        arch = self.env[model].get_views([(False, 'form')])['views']['form']['arch']
        return etree.fromstring(arch).xpath('//header/button')

    def _states(self, model):
        return [value for value, _label in self.env[model]._fields['state']._description_selection(self.env)]

    def test_at_most_one_primary_button_per_state(self):
        for model in STANDARD_FORMS:
            buttons = self._header_buttons(model)
            primaries = [b for b in buttons if 'btn-primary' in (b.get('class') or '').split()]
            self.assertTrue(primaries, f'{model}: no highlighted next-step button')
            self.assertFalse(
                [b.get('name') for b in buttons if 'oe_highlight' in (b.get('class') or '')
                 or set((b.get('class') or '').split()) & {'btn-success', 'btn-info', 'btn-warning'}],
                f'{model}: use btn-primary / btn-secondary only')
            # every name used in the invisible expressions, besides state, is treated as a boolean
            names = set()
            for button in primaries:
                names |= {node.id for node in ast.walk(ast.parse(button.get('invisible') or 'False', mode='eval'))
                          if isinstance(node, ast.Name)}
            flags = sorted(names - {'state', 'True', 'False'})
            for state in self._states(model):
                for combo in itertools.product((False, True), repeat=len(flags)):
                    values = dict(zip(flags, combo), state=state)
                    visible = [b.get('name') for b in primaries
                               if not safe_eval(b.get('invisible') or 'False', values)]
                    with self.subTest(model=model, values=values):
                        self.assertLessEqual(len(visible), 1, f'several primary buttons: {visible}')

    def test_every_role_loads_menus_and_standard_views(self):
        menu_root = self.env.ref('nt_construction.menu_tender_root')
        for role in ROLES:
            user = new_test_user(self.env, login=f'nt_ux_{role}', groups=f'nt_construction.group_construction_{role}')
            with self.subTest(role=role):
                menus = self.env['ir.ui.menu'].with_user(user).load_menus(debug=False)
                self.assertIn(menu_root.id, menus, f'{role} must see the Construction app')
                for model in STANDARD_FORMS:
                    if not self.env[model].with_user(user).has_access('read'):
                        continue
                    views = self.env[model].with_user(user).get_views(
                        [(False, 'form'), (False, 'list'), (False, 'search')])
                    self.assertEqual(set(views['views']), {'form', 'list', 'search'})

    def test_menu_business_order(self):
        root = self.env.ref('nt_construction.menu_tender_root')
        self.assertEqual(root.name, 'Construction')
        self.assertEqual(
            root.child_id.sorted('sequence').mapped('name'),
            ['Tenders', 'Projects', 'Execution', 'Contracts', 'Billing', 'Handover', 'Reporting'])
