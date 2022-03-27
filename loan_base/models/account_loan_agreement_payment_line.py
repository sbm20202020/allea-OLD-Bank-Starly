import math
from odoo import models, fields
from ..__odoo_future__ import to_date

ROUND_DIGITS = 2


def round_half_up(n, decimals=2):
    multiplier = 10 ** decimals
    return math.floor(n * multiplier + 0.5) / multiplier


class AccountLoanAgreementPaymentLine(models.Model):
    """Account Loan Agreement Payment Line"""

    _name = 'account.loan.agreement.payment.line'
    _order = 'date, priority'

    # Начисление в валюте компании
    accrual_in_company_currency = fields.Float(string='Accrual In Company Currency')
    # Начисление в валюте займа
    accrual_in_loan_currency = fields.Float(string='Accrual In Loan Currency')
    # Фактически начисленные проценты в валюте компании
    accrued_interest_fact_in_company_currency = fields.Float(string='Accrued Interest Fact In Company Currency')
    # Начисляемые проценты в валюте займа
    accrued_interest_fact_in_loan_currency = fields.Float(string='Accrued Interest Fact In Loan Currency')
    # Начисляемые проценты в валюте компании
    accrued_interest_in_company_currency = fields.Float(string='Accrued Interest in Company Currency')
    # Начисляемые проценты в валюте займа
    accrued_interest_in_loan_currency = fields.Float(string='Accrued Interest In Loan Currency')
    # Сумма в валюте оплаты
    amount_in_payment_currency = fields.Float(string='Amount In Payment Currency')
    company_currency_id = fields.Many2one(related='loan_agreement_id.company_currency_id', readonly=True)
    course1 = fields.Float(string='Course1', digits=(12, 6))
    course2 = fields.Float(string='Course2', digits=(12, 6), compute='_compute_course2')
    date = fields.Date(string='Payment Date')
    days = fields.Integer(string='Days')
    exchange_difference_loan_body = fields.Float(string='Exchange Difference of Loan Body')
    exchange_difference_loan_interest = fields.Float(string='Exchange Difference of Interest Loan')
    # Баланс процентов в валюте компании
    interest_balance_in_company_currency = fields.Float(string='Interest Balance in Company Currency')
    # Баланс процентов в валюте займа
    interest_balance_in_loan_currency = fields.Float(string='Interest Balance In Loan Currency')
    is_not_accrued_interest_fact_in_company_currency = fields.Boolean(
        compute='_compute_is_not_accrued_interest_fact_in_company_currency')
    line_type = fields.Selection([('calc', 'calc'), ('move', 'move')], default='calc')
    loan_agreement_id = fields.Many2one('account.loan.agreement', string='Corresponding Loan Agreement')
    # Сумма остатка по займу в валюте компании
    loan_amount_in_company_currency = fields.Float(string='Loan Balance Amount In Company Currency')
    # Сумма остатка по займу в валюте займа
    loan_amount_in_loan_currency = fields.Float(string='Loan Balance Amount In Loan Currency')
    # Баланс тела займа в валюте компании
    loan_body_balance_in_company_currency = fields.Float(string='Loan Body Balance in Company Currency')
    # Баланс тела займа в валюте займа
    loan_body_balance_in_loan_currency = fields.Float(string="The Balance Of The Loan Body In The Company's Currency")
    # Баланс тела займа в валюте займа (Красивый)
    loan_body_balance_in_loan_currency_beauty = fields.Float(
        string="The Balance Of The Loan Body In The Company's Currency")
    loan_currency_id = fields.Many2one(related='loan_agreement_id.loan_currency_id')
    loan_rate = fields.Float(string='Rate Value', related='loan_rate_id.value')
    loan_rate_id = fields.Many2one('account.loan.rate', string='Rate', compute='_compute_loan_rate_id')
    paid_amount = fields.Float(string='Paid Amount')  # Оплаченная Сумма
    # Оплаченные проценты в валюте компании
    paid_interest_in_company_currency = fields.Float(string='Paid Interest In Company Currency')
    # Оплаченные проценты в валюте займа
    paid_interest_in_loan_currency = fields.Float(string='Paid Interest In Loan Currency')
    past_due_payment = fields.Integer(string='Past Due Payment')
    payment_currency = fields.Many2one('res.currency', string='Payment Currency')  # Валюта оплаты
    payment_type = fields.Selection([('principal', 'Principal'), ('interest', 'Interest')], string='Type')
    posting_number = fields.Char(string='Posting Number')  # Номер Проводки
    priority = fields.Integer(default=10)
    # Погашение тела займа в валюте компании
    repayment_of_the_loan_body_in_the_company_currency = fields.Float(
        string="Repayment Of The Loan Body In The Company's Currency")
    # Погашение Тела Займа в валюте компании
    repayment_of_the_loan_body_in_the_loans_currency = fields.Float(
        string="Repayment Of The Loan Body In The Loan's Currency")
    # Тип транзакции
    transaction_type = fields.Selection([
        ('loan_drawdown', 'Loan Drawdown'),  # Начисление займа
        ('repayment_of_interest', 'Repayment of interest'),  # Погашение только процентов по займу
        ('repayment_of_principal', 'Repayment of principal'),  # Погашение только тела займа
        ('repayment_of_principal_and_interest', 'Repayment of principal and interest'),
        # Погашение процентов и тела займа
    ], string='Transaction Type')

    def _compute_course2(self):
        for payment_line in self:
            agreement = payment_line.loan_agreement_id
            loan_currency_id = agreement.loan_currency_id
            agreement_company_currency_id = agreement.company_currency_id
            rate = agreement_company_currency_id.with_context(date=payment_line.date)
            payment_line.course2 = rate.compute(1, loan_currency_id, round=False)

    def _compute_is_not_accrued_interest_fact_in_company_currency(self):
        for payment_line in self:
            payment_line.is_not_accrued_interest_fact_in_company_currency = not (
                    payment_line.accrued_interest_fact_in_company_currency > 0)

    def _compute_loan_rate_id(self):
        for payment_line in self:
            loan_rate_line_ids = payment_line.loan_agreement_id.loan_rate_line_ids
            payment_line.loan_rate_id = loan_rate_line_ids.filtered_by_date_and_return_rate_id(payment_line.date).id

    def _compute_accrual_in_loan_currency(self):
        for rec in self:
            result = rec.accrual_in_company_currency * rec.course2
            rec.accrual_in_loan_currency = round_half_up(result, decimals=ROUND_DIGITS)

    def _compute_repayment_of_the_loan_body_in_the_company_currency(self):
        for rec in self:
            result = -(rec.paid_interest_in_company_currency + rec.paid_amount)
            rec.repayment_of_the_loan_body_in_the_company_currency = round_half_up(result, decimals=ROUND_DIGITS)

    def _compute_repayment_of_the_loan_body_in_the_loans_currency(self):
        for rec in self:
            result = rec.repayment_of_the_loan_body_in_the_company_currency * rec.course2
            rec.repayment_of_the_loan_body_in_the_loans_currency = round_half_up(result, decimals=ROUND_DIGITS)

    def _compute_loan_body_balance_in_company_currency(self, prev_rec):
        self.ensure_one()
        rec = self
        result = (
                prev_rec.loan_body_balance_in_company_currency
                + rec.accrual_in_company_currency
                + rec.repayment_of_the_loan_body_in_the_company_currency
                + rec.exchange_difference_loan_body
        )
        rec.loan_body_balance_in_company_currency = round_half_up(result, decimals=ROUND_DIGITS)

    def _compute_loan_body_balance_in_loan_currency_beauty(self, prev_rec):
        self.ensure_one()
        rec = self
        result = (
                prev_rec.loan_body_balance_in_loan_currency_beauty
                + rec.accrual_in_loan_currency
                + rec.repayment_of_the_loan_body_in_the_loans_currency
        )
        rec.loan_body_balance_in_loan_currency_beauty = round_half_up(result, decimals=ROUND_DIGITS)

    def _compute_loan_body_balance_in_loan_currency(self):
        for rec in self:
            result = rec.loan_body_balance_in_company_currency * rec.course2
            rec.loan_body_balance_in_loan_currency = round_half_up(result, decimals=ROUND_DIGITS)

    def _compute_paid_interest_in_company_currency(self, prev_rec):
        self.ensure_one()
        rec = self
        paid_interest_in_company_currency_func_types = {
            'loan_drawdown': lambda rec, prev_rec: 0,  # Начисление займа #B2a
            'repayment_of_interest': lambda rec, prev_rec: -rec.paid_amount,  # Погашение только процентов по займу #B2b
            'repayment_of_principal': lambda rec, prev_rec: 0,  # Погашение только основной суммы займа #B2c
            # Погашение процентов и основной суммы займа #B2d
            'repayment_of_principal_and_interest': lambda rec, prev_rec: -(prev_rec.interest_balance_in_company_currency
                                                                           + rec.accrued_interest_in_company_currency)
        }
        paid_interest_in_company_currency_func = paid_interest_in_company_currency_func_types.get(rec.transaction_type,
                                                                                                  lambda rec,
                                                                                                         prev_rec: 0)
        result = paid_interest_in_company_currency_func(rec, prev_rec)
        rec.paid_interest_in_company_currency = round_half_up(result, decimals=ROUND_DIGITS)

    def _compute_paid_interest_in_loan_currency(self):
        for rec in self:
            result = rec.paid_interest_in_company_currency * rec.course2
            rec.paid_interest_in_loan_currency = round_half_up(result, decimals=ROUND_DIGITS)

    def get_accrued_interest_in_company_currency_without_exchange_difference(self, prev_rec):
        self.ensure_one()
        rec = self
        agreement_id = self.loan_agreement_id
        days_in_month, days_in_year = agreement_id.get_days(to_date(rec.date))
        result = prev_rec.loan_body_balance_in_company_currency * (rec.loan_rate * (rec.days / days_in_year))
        return result

    def _compute_accrued_interest_in_company_currency(self):
        self.ensure_one()
        rec = self
        try:
            result = rec.accrued_interest_in_loan_currency / rec.course2
            rec.accrued_interest_in_company_currency = round_half_up(result, decimals=ROUND_DIGITS)
        except ZeroDivisionError:
            rec.accrued_interest_in_company_currency = 0

    def _compute_accrued_interest_in_loan_currency(self, prev_rec, line_number):
        self.ensure_one()
        rec = self
        agreement_id = self.loan_agreement_id
        days_in_month, days_in_year = agreement_id.get_days(to_date(rec.date))
        if line_number == 0 and agreement_id.is_include_first_day:
            result = rec.loan_body_balance_in_loan_currency_beauty * (rec.loan_rate * (1 / days_in_year))
        elif line_number == 0:
            result = rec.accrued_interest_in_company_currency * rec.course2
        else:
            result = prev_rec.loan_body_balance_in_loan_currency_beauty * (rec.loan_rate * (rec.days / days_in_year))
        rec.accrued_interest_in_loan_currency = round_half_up(result, decimals=ROUND_DIGITS)

    def _compute_paid_amount(self):
        for rec in self:
            if rec.payment_currency and (rec.loan_currency_id != rec.payment_currency):
                result = rec.amount_in_payment_currency * rec.course2
            elif rec.payment_currency and (rec.loan_currency_id == rec.payment_currency):
                result = rec.amount_in_payment_currency * rec.course1
            else:
                result = 0
            rec.paid_amount = round_half_up(result, decimals=ROUND_DIGITS)

    def _compute_interest_balance_in_loan_currency(self, prev_rec):
        self.ensure_one()
        rec = self
        result = (
                prev_rec.interest_balance_in_loan_currency
                + rec.paid_interest_in_loan_currency
                + rec.accrued_interest_in_loan_currency
        )
        rec.interest_balance_in_loan_currency = round_half_up(result, decimals=ROUND_DIGITS)

    def _compute_interest_balance_in_company_currency(self, prev_rec):
        rec = self
        result = (
                prev_rec.interest_balance_in_company_currency
                + rec.paid_interest_in_company_currency
                + rec.accrued_interest_in_company_currency
                + prev_rec.exchange_difference_loan_interest
        )
        rec.interest_balance_in_company_currency = round_half_up(result, decimals=ROUND_DIGITS)

    def _compute_loan_amount_in_company_currency(self):
        for rec in self:
            try:
                result = rec.loan_amount_in_loan_currency / rec.course2
                rec.loan_amount_in_company_currency = round_half_up(result, decimals=ROUND_DIGITS)
            except ZeroDivisionError:
                rec.loan_amount_in_company_currency = 0

    def _compute_loan_amount_in_loan_currency(self, prev_rec):
        self.ensure_one()
        rec = self
        result = (
                prev_rec.loan_amount_in_loan_currency
                + rec.accrued_interest_in_loan_currency
                + rec.paid_interest_in_loan_currency
                + rec.accrual_in_loan_currency
                + rec.repayment_of_the_loan_body_in_the_loans_currency
        )
        rec.loan_amount_in_loan_currency = round_half_up(result, decimals=ROUND_DIGITS)

    def _compute_exchange_difference_loan_body(self, prev_rec):
        self.ensure_one()
        rec = self
        try:
            result = (prev_rec.loan_body_balance_in_company_currency * (prev_rec.course2 - rec.course2) / rec.course2)
            rec.exchange_difference_loan_body = round_half_up(result, decimals=ROUND_DIGITS)
            pass
        except ZeroDivisionError:
            rec.exchange_difference_loan_body = 0

    def _compute_exchange_difference_loan_interest(self):
        self.ensure_one()
        rec = self
        try:
            result = (rec.interest_balance_in_loan_currency / rec.course2 - rec.interest_balance_in_company_currency)
            rec.exchange_difference_loan_interest = round_half_up(result, decimals=ROUND_DIGITS)
            pass
        except ZeroDivisionError:
            rec.exchange_difference_loan_interest = 0
