{
    'name': "National Resignation ",
    'author': "National Technology",
    'website': "https://nt-me.com/",
    'category': 'Hr',
    'license': 'LGPL-3',

    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'survey', 'mail','hr'],

    # always loaded
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'security/recrord_rule.xml',
        'data/crons.xml',
        'data/template_of_exit_interview_email.xml',
        'views/views.xml',
        'views/hr_employee.xml',
        'views/hr_resignation.xml',
        'views/survey_view.xml',
        # 'views/survey_user_input_view.xml',
        'wizard/cancel_wizard.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
# -*- coding: utf-8 -*-
