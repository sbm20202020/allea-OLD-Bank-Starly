{
    "name": "VAT Report iCode",
    "summary": "VAT Report iCode",
    "version": "13.0.0.0.1",
    "category": "Reports",
    "website": "https://icode.by",
    "license": "AGPL-3",
    "application": True,
    "installable": True,
    "depends": [
        'account',
        'purchase',
        'hr_expense',
        'approvals_allea',
        'account_reports'
    ],
    "data": [
        # views
        'views/account_tax_report_line_views.xml',
        'views/purchase_order_views.xml',
        'views/account_tax_views.xml',
        'views/res_country_view.xml',
        'views/res_partner_view.xml',
        'views/account_analytic_tag_views.xml',
        'views/approval_request_views.xml',
        # 'views/account_move_views.xml',
        # wizard
        'wizard/vat_report_wizard_view.xml',
        'wizard/vat_report_export.xml',

    ],
    'post_init_hook': 'post_init_hook',
}
