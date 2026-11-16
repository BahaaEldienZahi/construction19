{
    'name': "National Clearance ",
    'author': "National Technology",
    'website': "https://nt-me.com/",
    'category': 'Hr',
    'license': 'LGPL-3',

    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'survey', 'mail','hr','nt_resignation'],

    # always loaded
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'data/clearance_report_templates.xml',
        'views/clearance_setup_views.xml',
        'views/clearance_request_views.xml',
        'views/menu_item.xml',
    ],
}
# -*- coding: utf-8 -*-
