# -*- coding: utf-8 -*-
{
    'name': 'NT Construction & Tender Management',
    'version': '19.0.1.0.0',
    'category': 'Operations/Construction',
    'summary': 'إدارة المناقصات والمقاولات - Tender to Project workflow with BOQ',
    'description': """
        Construction & Tender Management
        =================================
        - Tender lifecycle management (submission -> won/lost)
        - Conversion of won tenders into execution projects
        - BOQ (Bill of Quantities) management
        - Variation Orders with two-level approval
        - Subcontractor PO cost tracking against BOQ
        - Progress billing (Payment Certificates) with retention & advance recovery
        - Cost analysis & billing trend dashboards
        Compatible with Odoo 19.0 Community & Enterprise.
    """,
    'author': 'National Technology',
    'depends': [
        'base',
        'project',
        'purchase',
        'account',
        'analytic',
    ],
    'data': [
        'security/construction_security.xml',
        'security/ir.model.access.csv',
        'data/tender_sequence.xml',
        'data/construction_sequences.xml',
        'views/boq_line_views.xml',
        'views/tender_tender_views.xml',
        'views/project_project_views.xml',
        'views/purchase_order_views.xml',
        'views/boq_payment_certificate_views.xml',
        'views/dashboard_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
