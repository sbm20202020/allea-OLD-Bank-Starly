{
    "name": "Purchase Workflow iCode",
    "summary": "Purchase Workflow iCode",
    "version": "11.0.0.0.2",
    'author': 'iCode',
    "category": "Uncategorized",
    "website": "https://icode.by",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": [
        'hr',
        'account_budget',
        'agreements',
        'purchase',
        'purchase_requisition',
        'hr_timesheet',
    ],
    "data": [
        # security
        'security/rules.xml',
        # 'security/ir.model.access.csv',
        # views
        'views/account_analytic_account_views.xml',
        'views/account_budget_post_views.xml',
        'views/account_invoice_line_view.xml',
        'views/account_invoice_view.xml',
        'views/analytic_account_views.xml',
        'views/crossovered_budget_lines_views.xml',
        'views/crossovered_budget_views.xml',
        'views/purchase_order_views.xml',
        'views/product_template_views.xml',
        'views/account_analytic_line_views.xml',
        # wizard
        'wizard/stock_scheduler_compute_views.xml'
    ],
    "qweb": [

    ],
}
