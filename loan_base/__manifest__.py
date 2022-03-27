{
    "name": "Loans iCode",
    "summary": "Loans iCode",
    "version": "13.0.0.0.1",
    "category": "Invoicing",
    "website": "https://icode.by",
    "license": "AGPL-3",
    "application": True,
    "installable": True,
    "depends": [
        'base',
        'calendar',
        'account',
        'account_accountant',
        'inter_company_rules',
    ],
    "data": [
        # security
        'security/ir.model.access.csv',

        # data
        'data/ir_sequence_data.xml',
        'data/account_loan_agreement_stage.xml',
        'data/account_loan_rate_data.xml',

        # assets
        # 'views/assets_v12.xml',
        # 'views/assets_v11.xml',

        # views
        'views/account_move_views.xml',
        'views/account_move_line_views.xml',
        'views/account_bank_statement_views.xml',
        'views/account_loan_agreement_stage_views.xml',
        'views/account_loan_agreement_views.xml',
        # 'views/res_company_views.xml',
        'views/res_partner_views.xml',
        'views/account_reconcile_model_views.xml',
        'views/account_loan_rate_views.xml',

        # menus
        'views/loan_menus.xml',
    ],
    'external_dependencies': {'python': [
        'pandas',
        'numpy',
    ]},
}
