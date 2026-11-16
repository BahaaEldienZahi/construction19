{
    'name': "National Penalty And Reward",
    'summary': """
    """,
    'description': "",

    'author': "National Technology",
    'website': "https://nt-me.com/",
    'sequence': -100,
    'category': 'hr',
    'version': '0.1',
    'installable': True,
    'depends': ['base', 'hr', 'hr_payroll_community', 'hr_holidays', 'mail', 'hr_attendance', 'rm_hr_attendance_sheet',
                'compensation_leave'],
    'application': 'True',
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'wizard/penalty_reward_batch_views.xml',
        'wizard/add_refuse_reason_view.xml',
        'views/hr_contract.xml',
        'views/hr_employee.xml',
        'views/employee_penalty.xml',
        'views/employee_reward.xml',
        'views/employee_penalty_reward.xml',
        'views/menu.xml',
        'views/attendance_sheet.xml',
        'views/settings.xml',
    ],
    'web.assets_backend': [
        'nt_penalty_and_reward/static/src/js/basic_view.js'
    ]
}
