# -*- coding: utf-8 -*-
{
    'name': "Allowances and Deductions",
    'author': "National Technology",
    'website': "https://nt-me.com/",
    'category': 'Payroll',
    'version': '0.1',
    'license': 'LGPL-3',
    'depends': ['base', 'hr', 'hr_payroll_community'],
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/hr_contract_views.xml',
    ],
    'demo': [
        'demo/demo.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
