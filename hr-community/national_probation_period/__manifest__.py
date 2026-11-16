# -*- coding: utf-8 -*-
{
    'name': "Employee Probation Period",

    'summary': """
        """,
    'description': """
        
    """,
    'author': "National Technology",
    'website': "https://nt-me.com",
    'category': 'Hr',
    'version': '0.1',
    'license': 'LGPL-3',
    'depends': ['hr_contract', 'survey', 'hr', 'mail', 'hr_holidays', 'nt_resignation', 'hr_payroll_community'],
    'sequence': -200,

    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'data/update_probation_cron.xml',
        'views/hr_contract_view.xml',
        'views/timeoff_type.xml',
        'views/hr_employee_view.xml',
        'views/survey_user_input_view.xml',
        'views/employee_survey.xml',
        'views/employee_probation_period.xml',
        'views/probation_setting_views.xml',
        'views/menu.xml',
        # 'views/scheduled_actions.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': True,
}
