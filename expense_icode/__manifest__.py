{
    "name": "Expense iCode modifications",
    "summary": "Expense iCode modifications",
    "version": "0.1",
    "category": "Invoicing",
    "website": "https://icode.by",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": [
        'hr_expense',
    ],
    "data": [
        # security
        'security/ir.model.access.csv',
        # views
        # "views/hr_expense_views.xml",
        # "views/hr_expense_sheet_views.xml",
        # wizard
    ],
    "qweb": [

    ],
}
