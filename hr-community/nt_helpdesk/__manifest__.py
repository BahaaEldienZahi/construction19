# -*- coding: utf-8 -*-
{
    'name': "Helpdesk Customization",
    'author': "National Technology",
    'website': "https://nt-me.com/",
    'category': 'HelpDesk',
    'version': '0.1',
    'license': 'LGPL-3',
    'depends': ['base', 'helpdesk_mgmt', 'project', 'product', 'hr', 'account'],
    'data': [
        'security/helpdesk_security.xml',
        'security/ir.model.access.csv',
        'wizard/helpdesk_ticket_wizard_views.xml',
        'views/res_partner.xml',
        'views/helpdesk_product_views.xml',
        'views/helpdesk_area_views.xml',
        'views/helpdesk_ticket_log_views.xml',
        'views/helpdesk_ticket.xml',
        'views/helpdesk_category.xml',
        'views/product_views.xml',
        'views/helpdesk_stage.xml',
        'views/helpdesk_team.xml',
        'views/helpdesk_ticket_type_views.xml',
        'views/project_project_views.xml',
        'views/menu_views.xml',
        'data/cron_jobs.xml',
        'views/res_user_form_view.xml',
        'views/helpdesk_cr_views.xml'

    ],

    'installable': True,
    'application': True,
    'auto_install': False,
    'pre_init_hook': 'pre_init_hook',
}
