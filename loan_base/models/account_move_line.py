from odoo import models, fields, api

CHECK_PRECISION = 0.001


class AccountMoveLine(models.Model):
    """Account Move Line"""

    _inherit = 'account.move.line'

    loan_agreement_id = fields.Many2one('account.loan.agreement', string='Loan')

    def constrains_loan_agreement_id(self):
        self.ensure_one()
        loan_agreement_stage_validated = self.env.ref('loan_base.loan_agreement_stage_validated',
                                                      raise_if_not_found=False)
        loan_agreement_stage_provided = self.env.ref('loan_base.loan_agreement_stage_provided',
                                                     raise_if_not_found=False)
        move_line = self
        agreement_id = move_line.loan_agreement_id
        account_id = move_line.account_id
        move_line_date = move_line.date
        if agreement_id:
            loan_principal_account_id = agreement_id and agreement_id.loan_principal_account_id
            accrued_interest_account_id = agreement_id and agreement_id.accrued_interest_account_id
            debit = move_line.debit
            credit = move_line.credit
            is_debit_or_credit_has_value = debit >= 0 or credit >= 0
            payment_line_ids = agreement_id.payment_line_ids
            payment_lines_by_move_date = payment_line_ids.filtered(lambda r: r.date == move_line_date)
            is_zero_accrued_interest_fact_in_company_currency_by_the_day = payment_lines_by_move_date.filtered(
                'is_not_accrued_interest_fact_in_company_currency')
            no_recalc_entries_posting = self._context.get('no_recalc_entries_posting', False)
            if (is_zero_accrued_interest_fact_in_company_currency_by_the_day
                    and is_debit_or_credit_has_value
                    and not no_recalc_entries_posting):
                agreement_id.with_context(no_recalc_entries_posting=True).lunch_entries_posting_period(
                    until=move_line_date)

            is_principal_account = loan_principal_account_id.id == account_id.id
            is_interest_account = accrued_interest_account_id.id == account_id.id
            is_loan_account = is_principal_account or is_interest_account

            if is_loan_account:
                date_before = fields.Date.today()
                stage_id = agreement_id.stage_id
                principal_account_balance = loan_principal_account_id.get_balance(loan_agreement_id=agreement_id,
                                                                                  date_before=date_before)
                interest_account_balance = accrued_interest_account_id.get_balance(loan_agreement_id=agreement_id,
                                                                                   date_before=date_before)
                is_principal_account_zero_balance = abs(principal_account_balance) < CHECK_PRECISION
                is_interest_account_zero_balance = abs(interest_account_balance) < CHECK_PRECISION
                if stage_id.id == loan_agreement_stage_validated.id:
                    agreement_id.set_state_provided()
                elif (stage_id.id == loan_agreement_stage_provided.id and is_principal_account_zero_balance
                      and is_interest_account_zero_balance):
                    agreement_id.set_state_repaid()

    @api.constrains('loan_agreement_id')
    def _constrains_loan_agreement_id(self):
        for move_line in self:
            move_line.sudo().constrains_loan_agreement_id()

    # @api.model
    # def create(self, vals):
    #     check_move_validity = self._context.get('check_move_validity', False)
    #     move_line = super().create(vals)
    #     move_line.sudo().with_context(
    #         check_move_validity=check_move_validity).constrains_loan_agreement_id()
    #     return move_line

    def write(self, vals):
        result = super().write(vals)
        if 'loan_agreement_id' in vals:
            for move_line in self:
                move_line.sudo().constrains_loan_agreement_id()
        return result
