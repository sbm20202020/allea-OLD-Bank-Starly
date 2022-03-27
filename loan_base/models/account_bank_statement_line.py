from odoo import models, fields


class AccountBankStatementLine(models.Model):
    """Account Bank Statement Line"""

    _inherit = 'account.bank.statement.line'

    loan_agreement_id = fields.Many2one('account.loan.agreement')

    def get_data_for_reconciliation_widget(self, excluded_ids=None):
        result = super().get_data_for_reconciliation_widget(excluded_ids=excluded_ids)
        return result

    def reconciliation_widget_auto_reconcile(self, num_already_reconciled_lines):
        result = super().reconciliation_widget_auto_reconcile(num_already_reconciled_lines)
        return result

    def get_statement_line_for_reconciliation_widget(self):
        """ Returns the data required by the bank statement reconciliation widget to display a statement line
        Patching - added loan_agreement_id"""

        data = super().get_statement_line_for_reconciliation_widget()
        data['loan_agreement_id'] = self.loan_agreement_id.id

        return data

    def _prepare_reconciliation_move_line(self, move, amount):
        res = super()._prepare_reconciliation_move_line(move=move, amount=amount)
        res['loan_agreement_id'] = self.loan_agreement_id.id
        return res

    def get_balance_by_move_lines(self, move_lines=None):
        self.ensure_one()
        st_line = self
        line_residual = st_line.currency_id and st_line.amount_currency or st_line.amount
        total_residual = move_lines and sum(
            aml.currency_id and aml.amount_residual_currency or aml.amount_residual for aml in move_lines) or 0.0
        balance = total_residual - line_residual
        return balance

    # === BUSINESS LOGIC ===

    def get_principal_interest(self):
        """Called from JS Widget"""
        self.ensure_one()
        bank_statement_line_id = self
        vals = {
            'is_loan': False,
            'interest': 0,
            'principal': 0,
            'interest_account_id': 0,
            'interest_account_code': '',
            'principal_account_id': 0,
            'principal_account_code': '',
        }
        agreement_id = bank_statement_line_id.loan_agreement_id
        if agreement_id:
            loan_currency_id = agreement_id.loan_currency_id
            interest_account_id = agreement_id.accrued_interest_account_id
            principal_account_id = agreement_id.loan_principal_account_id
            balance = bank_statement_line_id.get_balance_by_move_lines()
            balance = abs(balance)  # TODO: fix this temporary solution <Pavel 2019-04-25>

            bank_statement_currency_id = bank_statement_line_id.statement_id.currency_id
            bank_statement_line_date = bank_statement_line_id.date
            if bank_statement_currency_id.id != loan_currency_id.id:
                date = bank_statement_line_date
                rate = bank_statement_currency_id.with_context(date=date)
                balance = rate.compute(balance, loan_currency_id, round=False)
                line1_balance, line2_balance = agreement_id.get_interest_principal_on_date_by_balance(
                    dt=bank_statement_line_date,
                    balance=balance,
                    amount_type='interest_first_principal_second')
                # возвращяем полученные значения в валюту bank statement'а
                reverse_rate = loan_currency_id.with_context(date=date)
                line1_balance = reverse_rate.compute(line1_balance, bank_statement_currency_id, round=False)
                line2_balance = reverse_rate.compute(line2_balance, bank_statement_currency_id, round=False)
            else:
                line1_balance, line2_balance = agreement_id.get_interest_principal_on_date_by_balance(
                    dt=bank_statement_line_date,
                    balance=balance,
                    amount_type='interest_first_principal_second')

            sign = 1 if agreement_id.is_receivable else -1
            vals.update(dict(
                is_loan=True,
                interest=line1_balance * sign,
                principal=line2_balance * sign,
                interest_account_id=interest_account_id.id,
                interest_account_code=interest_account_id.code,
                principal_account_id=principal_account_id.id,
                principal_account_code=principal_account_id.code,
            ))

        return vals
