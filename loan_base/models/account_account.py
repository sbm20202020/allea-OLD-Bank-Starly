from decimal import Decimal
from odoo import models


class Account(models.Model):
    """Account"""

    _inherit = 'account.account'

    def get_balance(self, date_before=None, loan_agreement_id=None):
        self.ensure_one()
        balance = 0
        account_move_line = self.env['account.move.line']
        account_id = self
        domain = [('account_id', '=', account_id.id)]
        if date_before:
            domain += [('date', '<=', date_before)]
        if loan_agreement_id:
            domain += [('loan_agreement_id', '=', loan_agreement_id.id)]
        move_lines = account_move_line.search(domain)
        amount_list = []
        for line in move_lines:
            debit = Decimal(line.debit).quantize(Decimal("1.00"))
            credit = Decimal(line.credit).quantize(Decimal("1.00"))
            amount = debit - credit
            amount_list.append(amount)
            balance += amount
        return balance
