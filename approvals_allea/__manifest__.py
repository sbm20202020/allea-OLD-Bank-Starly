{
    'name': 'Approvals Allea',
    'version': '13.0.0.01',
    'category': 'Approvals',
    'summary': 'Create and validate approvals requests to make business documents',
    'description': """
This module manages approvals workflow
======================================

This module manages approval requests like business trips,
out of office, overtime, borrow items, general approvals,
procurements, contract approval, etc.
    """,
    'depends': [
        'base',
        'approvals',
        'purchase',
        'product',
        'analytic',
        'agreements',
        'stock',
    ],
    'data': [
        'security/approval_security.xml',
        'security/ir.model.access.csv',
        # 'data/approval_category_data.xml',

        'views/approval_category_views.xml',
        'views/approval_request_views.xml',
        'views/product_template_views.xml',
        'views/account_analytic_account_views.xml',
        'views/purchase_order_views.xml',
    ],
    'application': False,
    'installable': True,
}
