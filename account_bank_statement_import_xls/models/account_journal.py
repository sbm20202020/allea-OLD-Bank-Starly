from odoo import models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def _get_bank_statements_available_import_formats(self):
        rslt = super(AccountJournal, self)._get_bank_statements_available_import_formats()
        rslt.append('XLS/XLSX')
        return rslt
