# -*- coding: utf-8 -*-
{
    'name': "National Employees",
    'summary': """ """,
    'description': """ """,
    'author': "National Technology",
    'website': "https://nt-me.com/",
    'category': 'Hr',
    'version': '0.1',
    "license": "AGPL-3",
    'depends': ['base', 'hr', 'account', 'hr_payroll_community', 'contacts', 'spreadsheet_dashboard', 'hr_timesheet',
                'hr_holidays', 'hr_gamification'],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'security/record_rules.xml',
        'views/hr_employee.xml',
        'views/address_book_views.xml',
        'views/res_config_settings.xml',
        'views/menus.xml',
        'data/cron.xml'
    ],
}
