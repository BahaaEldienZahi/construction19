# -*- coding: utf-8 -*-
{
    'name': "NT Compensation Leave",
    'author': "National Technology",
    'website': "https://nt-me.com/",
    'category': 'Time Off',
    'version': '0.1',
    "license": "AGPL-3",
    'depends': ['base', 'hr_holidays', 'hr_payroll_community','nt_hr_permission_time_off'],
    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'data/data.xml',
        'views/views.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
