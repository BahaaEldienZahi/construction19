from odoo.tests.common import TransactionCase

class TestCI(TransactionCase):
    def test_should_fail(self):
        self.assertEqual(1, 2)