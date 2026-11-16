# -*- coding: utf-8 -*-
{
    'name': "Hiring Request",

    'summary': "Hiring Cycle",

    'description': """Hiring Request Cycle""",

    'author': "National Technology",

    'depends': ['base', 'mail', 'hr', 'hr_recruitment', 'nt_recruitment_update'],

    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        # 'data/mail_template.xml',
        'wizard/hiring_rejection_reason_wizard.xml',
        'views/hr_department.xml',
        'views/hiring_request.xml',
    ],
}
