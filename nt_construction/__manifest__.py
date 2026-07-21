# -*- coding: utf-8 -*-
{
    'name': 'NT Construction & Tender Management',
    'version': '19.0.2.0.0',
    'category': 'Operations/Construction',
    'summary': 'إدارة المناقصات والمقاولات - Tender to Project workflow with BOQ',
    'description': """
        Construction & Tender Management — Full Suite
        ==============================================
        تدبير كامل للمقاولات من المناقصة لحد التسليم النهائي:

        🔹 Tender lifecycle (submission → evaluation → won/lost → execution project)
        🔹 BOQ (Bill of Quantities) with full hierarchy (Chapter → Item → Sub-item)
        🔹 Variation Orders with two-level approval & auto-apply to BOQ
        🔹 Subcontractor Agreements with per-BOQ-line cost tracking & two-level approval
        🔹 Subcontractor Payment Certificates (مستخلصات مقاولي الباطن) + Vendor Bill creation
        🔹 Payment Certificates (مستخلصات العميل) with retention, advance recovery & invoicing
        🔹 Site Daily Reports / Sarky (تقرير يومي بالعمالة والمعدات والكميات المنفذة)
        🔹 Work Measurement (قياس أعمال) — groups daily reports into billing periods with BOQ aggregation
        🔹 Material Requisitions (طلبات صرف مواد من الموقع)
        🔹 Work Inspections — WIR/MIR (طلبات فحص الأعمال والمواد)
        🔹 Project Correspondence (مراسلات وخطابات الموقع)
        🔹 Site Progress Photos (توثيق صور تقدم الأعمال)
        🔹 Bank Guarantees (خطابات الضمان البنكية — Bid Bond, Performance, Advance Payment, Retention)
        🔹 Quantity-based billing flow: Daily Report → Work Measurement → Payment Certificate
        🔹 Project Handover / Delivery (تسليم ابتدائي ونهائي) with:
           - Defects Liability Period (DLP)
           - Punch List / Snag List
           - Two-stage retention release
        🔹 Smart buttons on project form: BOQ, Subcontracts, Daily Reports, Handovers,
           Requisitions, Inspections, Correspondence, Photos, Guarantees
        🔹 Cost analysis dashboards (Contracted vs Committed vs Executed vs Actual Cost)
        🔹 Billing trend pivot & graphs
        🔹 Actual cost tracking from vendor bills
        🔹 Load Payment Certificate lines directly from Work Measurement

        Compatible with Odoo 19.0 Community & Enterprise.
    """,
    'author': 'National Technology',
    'depends': [
        'base',
        'project',
        'purchase',
        'account',
        'analytic',
        'stock',
    ],
    'data': [
        'security/construction_security.xml',
        'security/construction_record_rules.xml',
        'security/ir.model.access.csv',
        'data/tender_sequence.xml',
        'data/construction_sequences.xml',
        'data/material_requisition_cron.xml',
        'views/boq_line_views.xml',
        'views/project_project_views.xml',
        'views/purchase_order_views.xml',
        'views/material_requisition_views.xml',
        'views/work_inspection_views.xml',
        'views/project_correspondence_views.xml',
        'views/site_progress_photo_views.xml',
        'views/bank_guarantee_views.xml',
        # menu_structure.xml must load here (before the files below): it
        # defines the root menu (menu_tender_root) and the 4 submenus
        # (menu_tender_management, menu_project_execution, menu_commercial,
        # menu_handover_section) that every file below attaches its own
        # menuitem to via parent="menu_commercial" / etc. It is now
        # self-contained (defines menu_tender_root internally) so it no
        # longer needs to wait for tender_tender_views.xml.
        'views/menu_structure.xml',
        'views/project_handover_views.xml',
        'views/load_certificate_wizard_views.xml',
        'views/tender_tender_views.xml',
        'views/boq_payment_certificate_views.xml',
        'views/boq_variation_order_views.xml',
        'views/site_daily_report_views.xml',
        'views/work_measurement_views.xml',
        'views/subcontract_agreement_views.xml',
        'views/subcontract_payment_certificate_views.xml',
        'views/dashboard_views.xml',

        'reports/report_tender_tender.xml',
        'reports/report_boq_payment_certificate.xml',
        'reports/report_subcontract_agreement.xml',
        'reports/report_subcontract_payment_certificate.xml',
        'reports/report_boq_variation_order.xml',
        'reports/report_site_daily_report.xml',
        'reports/report_work_measurement.xml',
        'reports/report_material_requisition.xml',
        'reports/report_work_inspection.xml',
        'reports/report_project_handover.xml',
        'reports/report_bank_guarantee.xml',






    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
