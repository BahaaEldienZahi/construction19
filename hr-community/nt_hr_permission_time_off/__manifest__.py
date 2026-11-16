# -*- coding: utf-8 -*-
{
    'name': "Hr Permission Time Off",
    'author': "National Technology",
    'website': "https://nt-me.com/",
    'category': 'Uncategorized',
    'version': '0.1',
    'depends': ['base', 'hr','hr_holidays', 'project', 'nt_customer_vendor'],
    'data': [
        # 'security/ir.model.access.csv',
        'views/hr_leave_type_views.xml',
        'views/hr_leave.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
