{
    "name": "Budgets",
    "summary": "Extend work with budgets",
    "version": "13.0.0.0.1",
    'author': "Solopov Nikita",
    "category": "Analytic Accounting",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": [
        'account_budget',
        'account',
        'hr',
    ],
    "data": [
        # security
        # 'security/rules.xml',
        # 'security/ir.model.access.csv',
        # views
        'views/account_analytic_account_views.xml',
        'views/account_budget_post_views.xml',
        # 'views/account_invoice_line_view.xml',
        # 'views/account_invoice_view.xml',
        # 'views/analytic_account_views.xml',
        'views/crossovered_budget_lines_views.xml',
        # 'views/purchase_order_views.xml',
        # 'views/product_template_views.xml',
        # 'views/account_analytic_line_views.xml',
        # wizard
        'wizard/stock_scheduler_compute_views.xml'
    ],
    "qweb": [

    ],
}
