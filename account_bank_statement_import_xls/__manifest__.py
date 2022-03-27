# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Import XLS/XLSX Bank Statement',
    'category': 'Accounting/Accounting',
    'version': '1.0',
    'depends': ['account_bank_statement_import'],
    'description': """
Module to import XLS/XLSX bank statements.
======================================

This module allows you to import the machine readable XLS/XLSX Files in Odoo: they are parsed and stored in human readable format in
Accounting \ Bank and Cash \ Bank Statements.

    """,
    'data': [
        'wizard/account_bank_statement_import_views.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
}
