# -*- coding: utf-8 -*-

{
    "name": "Customer Vendor",
    'author': "National Technology",
    'website': "https://nt-me.com",
    "license": "OPL-1",
    "summary": """
    Customer Vendor for sale, purchase and account
    """,
    "description": """
    Customer Vendor for sale, purchase and account
    """,
    "depends": ["sale_management", 'sales_team', "purchase", "contacts", 'account','crm'],
    "data": [
        "views/account_move_views.xml",
        "views/res_partner_views.xml",
        "views/sale_order_views.xml",
        "views/purchase_order_views.xml",
        # "views/bank_statement_views.xml"
    ],
}
