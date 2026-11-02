import datetime as dt
import re

from odoo.tests import TransactionCase, tagged
from odoo.tools.misc import format_amount, format_date, format_datetime

NON_WESTERN_DIGIT = re.compile(r'[٠-٩۰-۹]')  # Arabic-Indic and Persian digits


@tagged('post_install', '-at_install', 'nt_construction')
class TestArabicDigits(TransactionCase):
    """DECISIONS S9: Arabic UI with Western digits (0-9) via the ar_EG language record."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['res.lang']._activate_lang('ar_EG')
        cls.lang = cls.env.ref('nt_construction.lang_ar_eg')

    def test_language_record(self):
        self.assertTrue(self.lang.active)
        self.assertEqual(self.lang.direction, 'rtl')
        self.assertEqual(self.lang.code, 'ar_EG')

    def test_server_side_formats_use_western_digits(self):
        env = self.env(context={'lang': 'ar_EG'})
        values = [
            format_date(env, dt.date(2026, 11, 2)),
            format_datetime(env, dt.datetime(2026, 11, 2, 13, 45)),
            format_amount(env, 1234567.89, env.company.currency_id),
        ]
        for value in values:
            with self.subTest(value=value):
                self.assertRegex(value, r'[0-9]')
                self.assertIsNone(NON_WESTERN_DIGIT.search(value))
        self.assertEqual(values[0], '02/11/2026')
