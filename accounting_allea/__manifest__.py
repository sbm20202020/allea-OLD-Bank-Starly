# -*- coding: utf-8 -*-
{
    'name': 'Accounting Modifications',
    'version': '13.0.0.1',
    'summary': 'Accounting Modifications',
    'author': 'Solopov Nikita',
    'depends': [
        'account',
        'purchase',
        'approvals_allea'
        # 'currency_rate_live'
        # 'account_reports',
    ],
    'data': [
        # security
        # 'security/security.xml',

        # views
        # 'views/general_ledger_reversed_filter.xml',
        # 'views/account_trial_balance_view.xml',
        # 'views/res_partner_restrict.xml',
        # 'views/templates.xml',
        # 'views/account_report_ledger_view.xml',
        # 'views/report_generalledger.xml',
        # 'views/report_financial.xml',
        'views/purchase_views.xml',
        'views/account_move_line_views.xml',
        'views/account_account_views.xml',

        # data
        # 'data/data_account_type.yml',
        # 'data/ir_cron_data.xml',

        # wizard
        # 'wizard/account_report_bscfpl_wizard_view.xml',
        # 'wizard/account_report_general_ledger_view.xml',
        'wizard/account_draft_move_view.xml',
    ],
    'auto_install': False,
    'installable': True,
}
