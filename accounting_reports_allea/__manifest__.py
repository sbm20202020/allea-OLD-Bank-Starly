{
    'name': 'Accounting Reports Allea',
    'version': '13.0.0.1',
    'category': 'Accounting',
    'summary': 'Make changes in default Accounting Reports by wishes Allea Group',
    'description': """
This module manages Accounting Reports
======================================

This module change default algorithm of standard accounting reports.
    """,
    'depends': [
        'account',
        'account_reports',
        'account_budget'
    ],
    'data': [
        'data/account_financial_report_data.xml',
        'report/report_financial.xml',
        'wizard/accounts_budgets_wizard_view.xml',
    ],
    'application': False,
    'installable': True,
    'external_dependencies': {
        'python': ['pandas'],
    }
}
