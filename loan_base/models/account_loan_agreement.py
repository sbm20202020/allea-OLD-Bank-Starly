import logging
# === Standard library imports ===
from operator import itemgetter
from collections import defaultdict
from datetime import datetime, date
from dateutil.rrule import rrule, MONTHLY, DAILY
from dateutil.relativedelta import relativedelta
from calendar import isleap, monthrange
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

FILTERED_DATE = date(2019, 12, 31)
_logger = logging.getLogger(__name__)

try:
    from pandas import DataFrame, pivot_table
    import numpy as np
except ImportError:
    _logger.warning('The `pandas` Python module is not installed, pip install pandas numpy')

# === CONSTANTS ==================
PERIOD_VARIANTS = [
    ('once_a_day', 'Once a day'),
    ('once_in_n_days', 'Once in N days'),
    ('once_a_week', 'Once a week'),
    ('once_in_n_months', 'Once in N months'),
    ('once_a_month_certain_date', 'Once a month - certain date'),
    ('for_n_days_till_the_end_of_month', 'For N days till the end of month'), ]

MOVE_THRESHOLD = 0.01


class LoanAgreement(models.Model):
    """Loan Agreement"""
    _name = 'account.loan.agreement'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # === Default method and ``_default_get``
    def _default_stage_id(self):
        stages = self.env['account.loan.agreement.stage'].sudo().search([('fold', '=', False)], order='sequence',
                                                                        limit=1)
        return stages[:1].id

    def _default_name(self):
        loan_agreement_sequence = self.env.ref('loan_base.loan_agreement_sequence', raise_if_not_found=False)
        next_num = loan_agreement_sequence.next_by_id()
        return 'LA {0}'.format(next_num)

    def _default_drawdown_date(self):
        if self.payment_line_ids:
            for line in self.payment_line_ids:
                if line.accrual_in_company_currency > 0:
                    return line.date
        else:
            return False

    # === Field declarations
    accrued_interest_account_id = fields.Many2one('account.account', string='Accrued Interest Account')  # #M1a10
    agreement_date = fields.Date('Agreement Date', default=fields.Date.today())  # #M1a3 # Дата договора
    bank_account_id = fields.Many2one('account.account', string='Bank Account')
    borrower_company_pid = fields.Many2one('res.partner', string='Borrower',
                                           domain="[('is_borrower', '=', True)]")  # #M1a7 # Дебитор
    company_currency_id = fields.Many2one('res.currency')  # #M1CCY #M1a12
    company_id = fields.Many2one('res.company')
    current_interest = fields.Float()
    current_principal = fields.Float()
    day_count_convention = fields.Selection(  # #M1c
        [('30_360', '30/360'),  # #M1c1
         ('30_365', '30/365'),  # #M1c2
         ('actual_360', 'Actual/360'),  # #M1c3
         ('actual_365', 'Actual/365'),  # #M1c4
         ('actual_actual', 'Actual/Actual'),  # #M1c5
         ], string='Day Count Convention', default='30_360')
    drawdown_date = fields.Date('Drawdown Date',
                                default=lambda self: self._default_drawdown_date())  # # Дата начисления (Факт)
    entries_posting_period_from = fields.Date('Entries Posting Period From')
    entries_posting_period_to = fields.Date('Entries Posting Period To')
    expected_drawdown_date = fields.Date('Expected Drawdown Date',
                                         default=fields.Date.today())  # #M1a4 # Дата начисления (План)
    interest_accrual_date = fields.Date(string='Interest Accrual Date', compute='_compute_interest_accrual_date')
    interest_accrual_date_custom = fields.Date(string='Interest Accrual Date Custom', default=fields.Date.today())
    interest_accrual_date_type = fields.Selection([("today_date", "Today's date"), ('custom', 'Custom')],
                                                  'Interest Accrual Date', default='today_date')
    interest_accrual_dates = fields.Char('Interest Accrual Dates', default='End of month, every transaction date')
    interest_calculation_parameters = fields.Char('Interest Calculation Parameters', default='Simple Interest')
    interest_move_line_ids = fields.One2many('account.move.line', compute='_compute_interest_move_line_ids',
                                             inverse='_inverse_interest_move_line_ids')
    interest_outstanding = fields.Float(string='Interest Outstanding', compute='_compute_interest_outstanding',
                                        store=False)  # #M2b5 compute balance of #M1a10
    interest_outstanding_on_date = fields.Monetary(string='Interest Outstanding',
                                                   currency_field='loan_currency_id')  # #M2b5 compute balance of #M1a10
    interest_payable_account_id = fields.Many2one('account.account', string='Interest Payable Account')
    interest_rate_type = fields.Selection([('fixed', 'Fixed'), ('floating', 'Floating')], string='Interest Rate Type',
                                          default='fixed')  # #M1d1
    interest_receivable_account_id = fields.Many2one('account.account', string='Interest Receivable Account')
    is_include_first_day = fields.Boolean('is include first day')
    is_long_term_loan = fields.Boolean(compute='_compute_is_long_term_loan', store=True)
    is_receivable = fields.Boolean('Is Receivable', compute='_compute_is_receivable')
    journal_type = fields.Char(compute='_compute_journal_type')
    lender_company_pid = fields.Many2one('res.partner', string='Lender',
                                         domain="[('is_lender', '=', True)]")  # #M1a6 # Кредитор
    loan_currency_id = fields.Many2one('res.currency', default=lambda self: self.env.user.company_id.currency_id,
                                       string='Loan Currency', required=True)  # #M1a2
    loan_principal_account_id = fields.Many2one('account.account', string='Loan Principal Account')  # #M1a11
    loan_rate = fields.Float('Rate Value', related='loan_rate_id.value')  # #M1d1
    loan_rate_id = fields.Many2one('account.loan.rate', string='Rate', required=True)
    loan_rate_line_ids = fields.One2many('account.loan.rate.line', 'agreement_id', string='Loan Rate History Lines')
    loan_term = fields.Integer('Loan Term', default=0)  # #M1a8
    loan_type = fields.Selection([('receivable', 'Receivable'), ('payable', 'Payable')], string='Loan Type',
                                 default='receivable')
    loan_value = fields.Float(string='Loan Value')  # Сумма займа (План)
    move_ids = fields.One2many('account.move', compute='_compute_move_ids', inverse='_inverse_move_ids')
    name = fields.Char('Loan Number', default=lambda self: self._default_name())
    opposite_loan_agreement_id = fields.Many2one('account.loan.agreement', 'Opposite Loan')
    payment_line_ids = fields.One2many('account.loan.agreement.payment.line', 'loan_agreement_id',
                                       string='Payment Lines')
    payment_start_date = fields.Date('Payment Start Date', default=fields.Date.today())
    planned_settlement_date = fields.Date('Planned Settlement Date',
                                          default=fields.Date.today())  # Дата планируемого погашения
    principal_outstanding = fields.Float(string='Principal Outstanding', compute='_compute_principal_outstanding',
                                         store=False)  # Баланс Тела Займа
    principal_outstanding_on_date = fields.Monetary(string='Principal Outstanding', currency_field='loan_currency_id')
    repayment_line_ids = fields.One2many('account.loan.agreement.repayment.line', 'loan_agreement_id',
                                         string='Repayment Schedule Lines')
    rule_id = fields.Many2one('account.reconcile.model', string='Corresponding rule')
    settlement_schedule = fields.Selection([('free', 'Free'), ('fixed', 'Fixed')], string='Settlement Schedule',
                                           default='free')
    stage_id = fields.Many2one('account.loan.agreement.stage', string='Stage', track_visibility='onchange', index=True,
                               group_expand='_read_group_stage_ids', default=lambda self: self._default_stage_id())
    status = fields.Selection([('draft', 'Draft'),
                               # Договор займа создан, но не отображается у связанной компании,
                               #  являющейся контрагентом по сделке (может быть удален из системы).

                               ('validated', 'Validated'),
                               # Договор займа подтвержден и отображается у связанной компании,
                               #  являющейся контрагентом по сделке (не может быть более удален из системы).

                               ('provided', 'Provided'),
                               # Займ предоставлен. Статус проставляется после отражения операции
                               #  начисления займа по счету по учету тела займа.

                               ('repaid', 'Repaid'),
                               # Займ и проценты по нему выплачены. Статус проставляется после отражения
                               #  нулевых остатков на счетах по учету тела и процентов займа.

                               ('written_off', 'Written-off'),  # #M2d2
                               # Займ отмечен как списанный. Проводка генерируется вручную.

                               ('zeroed_out', 'Zeroed Out'),  # Займ обнулен. Проводка генерируется вручную.

                               ('removed_from_computation', 'Removed From Computation'),  # #M2d4
                               # Займ убран из дальнейшего расчета. Проводка генерируется вручную.
                               ])
    today_date = fields.Datetime(compute='_compute_today_date')  # #M2a1
    total_outstanding = fields.Float(string='Total Outstanding', compute='_compute_total_outstanding',
                                     store=False)  # #M2b2
    total_outstanding_on_date = fields.Monetary(string='Total Outstanding',
                                                compute='_compute_total_outstanding_on_date', store=True,
                                                currency_field='loan_currency_id')
    transactions_journal_id = fields.Many2one('account.journal', string="Transactions Journal",
                                              domain="[('company_id', '=', company_id), ('type', '=', journal_type)]")
    unr_exchange_gain_account_id = fields.Many2one('account.account',
                                                   string='Unr. Exchange Gain Account')
    unr_exchange_gain_loss_journal_id = fields.Many2one('account.journal', string='Unr. Exchange Gain/Loss Journal')
    unr_exchange_loss_account_id = fields.Many2one('account.account',
                                                   string='Unr. Exchange Loss Account')

    def _compute_move_ids(self):
        move_line = self.env['account.move.line']
        for agreement_id in self:
            move_ids = move_line.sudo().search([('loan_agreement_id', '=', agreement_id.id)]).mapped('move_id')
            agreement_id.move_ids = [[6, 0, move_ids.ids]]

    def _inverse_move_ids(self):
        move_line = self.env['account.move.line']
        for agreement_id in self:
            move_ids = move_line.sudo().search([('loan_agreement_id', '=', agreement_id.id)]).mapped('move_id')
            unlink_ids = move_ids - agreement_id.move_ids
            unlink_ids.unlink()

    def _compute_interest_move_line_ids(self):
        move_line = self.env['account.move.line']
        for agreement_id in self:
            interest_move_line_ids = move_line.sudo().search([('loan_agreement_id', '=', agreement_id.id), (
                'account_id', '=', agreement_id.accrued_interest_account_id.id)])
            agreement_id.interest_move_line_ids = [[6, 0, interest_move_line_ids.ids]]

    def _inverse_interest_move_line_ids(self):
        move_line = self.env['account.move.line']
        for agreement_id in self:
            interest_move_line_ids = move_line.sudo().search([('loan_agreement_id', '=', agreement_id.id), (
                'account_id', '=', agreement_id.accrued_interest_account_id.id)])
            unlink_ids = interest_move_line_ids - agreement_id.interest_move_line_ids
            unlink_ids.unlink()

    # === Compute, inverse and search methods in the same order as field declaration
    @api.depends('loan_principal_account_id', 'accrued_interest_account_id')
    def _compute_total_outstanding(self):
        for agreement in self:
            agreement.total_outstanding = agreement.principal_outstanding + agreement.interest_outstanding

    @api.depends('loan_principal_account_id')
    def _compute_principal_outstanding(self):
        for agreement in self:
            if agreement.loan_principal_account_id.id:
                agreement.principal_outstanding = agreement.loan_principal_account_id.get_balance(
                    loan_agreement_id=agreement)
            else:
                agreement.principal_outstanding = 0

    @api.depends('accrued_interest_account_id')
    def _compute_interest_outstanding(self):
        for agreement in self:
            if agreement.accrued_interest_account_id.id:
                agreement.interest_outstanding = agreement.accrued_interest_account_id.get_balance(
                    loan_agreement_id=agreement)
            else:
                agreement.interest_outstanding = 0

    @api.onchange('loan_term', 'payment_start_date', 'settlement_schedule')
    @api.constrains('loan_term', 'payment_start_date', 'settlement_schedule')
    def _compute_planned_settlement_date(self):
        for agreement in self:
            if agreement.settlement_schedule == 'fixed':
                # actual_actual case
                months = agreement.loan_term
                date_from = agreement.payment_start_date
                date_from, = map(fields.Date.to_date, [date_from])
                agreement.planned_settlement_date = date_from + relativedelta(months=months)  # + relativedelta(days=1)

    @api.onchange('payment_start_date', 'planned_settlement_date')
    @api.constrains('payment_start_date', 'planned_settlement_date')
    def _onchange_payment_start_date_planned_settlement_date(self):
        for agreement in self:
            if agreement.settlement_schedule == 'free':
                date_from = agreement.payment_start_date
                date_to = agreement.planned_settlement_date
                date_from, date_to = map(fields.Date.to_date, [date_from, date_to])
                agreement.loan_term = len([dt for dt in rrule(MONTHLY, dtstart=date_from, until=date_to)]) - 1

    @api.onchange('borrower_company_pid', 'lender_company_pid', 'loan_type')
    @api.constrains('borrower_company_pid', 'lender_company_pid', 'loan_type')
    def _onchange_company_id_currency_id(self):
        account_journal = self.env['account.journal']
        for agreement in (r for r in self if r.loan_type in ('receivable', 'payable')):
            # TODO: check loan_type check logic <Pavel 2019-03-22>
            company_pid = False
            company_id = False
            if agreement.loan_type == 'payable':
                company_pid = agreement.borrower_company_pid
            elif agreement.loan_type == 'receivable':
                company_pid = agreement.lender_company_pid
            if company_pid:
                company_id = self.env['res.company'].search([('partner_id', '=', company_pid.id)], limit=1)
            if company_id:
                agreement.company_currency_id = company_id.currency_id.id
                agreement.company_id = company_id.id

                # setting corresponding transactions journal
                transactions_journal_id = account_journal.search([
                    ('type', '=', agreement.journal_type), ('company_id', '=', agreement.company_id.id)], limit=1)
                if not transactions_journal_id.id:
                    transactions_journal_id = account_journal.create(
                        {
                            'name': 'Journal Receivable' if agreement.journal_type == 'journal_receivable'
                            else 'Journal Payable',
                            'type': agreement.journal_type,
                            'code': 'jr' if agreement.journal_type == 'journal_receivable' else 'jp',
                            'company_id': agreement.company_id.id})
                agreement.transactions_journal_id = transactions_journal_id.id
            else:
                agreement.company_currency_id = False
                agreement.company_id = False

    @api.depends('loan_term', 'payment_start_date')
    def _compute_is_long_term_loan(self):
        for agreement in self:
            if agreement.loan_term > 24:
                agreement.is_long_term_loan = True
            else:
                agreement.is_long_term_loan = False

    def _compute_today_date(self):
        for rec in self:
            rec.today_date = fields.Datetime.now()

    @api.onchange('loan_term', 'payment_start_date', 'day_count_convention', 'loan_value', 'loan_rate_id')
    @api.constrains('loan_term', 'payment_start_date', 'day_count_convention', 'loan_value', 'loan_rate_id')
    def _onchange_repayment_line_ids(self):
        """
        compute for differentiated Payment Type
        for Annuity Payment Type should be extended
        """
        repayment_line = self.env['account.loan.agreement.repayment.line']
        agreements = [self] if len(self) == 1 else self
        for agreement in agreements:
            repayment_lines = repayment_line
            date_from = agreement.payment_start_date
            date_to = agreement.planned_settlement_date
            date_from, date_to = map(fields.Date.to_date, [date_from, date_to])
            dates = [dt for dt in rrule(MONTHLY, dtstart=date_from, until=date_to)]
            try:
                period_payment = agreement.loan_value / agreement.loan_term
            except ZeroDivisionError:
                period_payment = 0

            principal_outstanding = agreement.loan_value  # for debug purposes
            for i, dt in enumerate(dates[:-1], 1):
                days_in_month, days_in_year = agreement.get_days(dt)
                interest = principal_outstanding * (agreement.loan_rate * (days_in_month / days_in_year))
                val = dict(
                    loan_agreement_id=agreement.id,
                    date=fields.Date.to_string(dt),
                    principal=period_payment,
                    interest=interest,
                    total_payment=period_payment + interest,
                )
                principal_outstanding -= period_payment
                repayment_lines += repayment_line.new(val)
            agreement.repayment_line_ids = repayment_lines

    def _compute_interest_accrual_date(self):
        for rec in self:
            if rec.interest_accrual_date_type == 'today_date':
                rec.interest_accrual_date = fields.Date.today()
            elif rec.interest_accrual_date_type == 'custom':
                rec.interest_accrual_date = rec.interest_accrual_date_custom

    def button_compute_interest_outstanding_on_date(self):
        # TODO: переделать на функцию принимающую и отдающую параметры <Pavel 2019-07-26>
        for agr in self:
            agr.button_get_moves()
            agr.payment_line_ids.filtered(lambda rec: rec.priority == 1000).unlink()
            agr.payment_line_ids = [(0, 0, {'priority': 1000, 'date': agr.interest_accrual_date})]
            agr.button_compute_table()
            agr.interest_outstanding_on_date = agr.payment_line_ids.filtered(
                lambda rec: rec.priority == 1000).interest_balance_in_loan_currency
            agr.principal_outstanding_on_date = agr.payment_line_ids.filtered(
                lambda rec: rec.priority == 1000).loan_body_balance_in_loan_currency

    @api.depends('loan_type')
    def _compute_journal_type(self):
        for agreement in self:
            if agreement.loan_type == 'payable':
                agreement.journal_type = 'journal_payable'
            elif agreement.loan_type == 'receivable':
                agreement.journal_type = 'journal_receivable'
            else:
                agreement.journal_type = False

    @api.depends('principal_outstanding_on_date', 'interest_outstanding_on_date')
    def _compute_total_outstanding_on_date(self):
        for agreement in self:
            agreement.total_outstanding_on_date = (agreement.principal_outstanding_on_date
                                                   + agreement.interest_outstanding_on_date)

    def _compute_is_receivable(self):
        for agreement in self:
            agreement.is_receivable = agreement.loan_type == 'receivable'

    # === Selection method (methods used to return computed values for selection fields)

    # === Constrains methods (``@api.constrains``) and onchange methods (``@api.onchange``)

    @api.constrains('stage_id')
    def _constrains_stage_id(self):
        loan_agreement_stage_provided = self.env.ref('loan_base.loan_agreement_stage_provided',
                                                     raise_if_not_found=False)
        for agreement in self:
            if (agreement.opposite_loan_agreement_id.id
                    and agreement.sudo().opposite_loan_agreement_id.stage_id.id != agreement.stage_id.id):
                agreement.sudo().opposite_loan_agreement_id.stage_id = agreement.stage_id.id

    @api.onchange('loan_type')
    @api.constrains('loan_type')
    def _onchange_loan_type(self):
        agreements = (self,) if len(self) == 1 else self
        for agreement in agreements:
            if agreement.loan_type == 'payable':
                agreement.borrower_company_pid = self.env.company.partner_id.id
            elif agreement.loan_type == 'receivable':
                agreement.lender_company_pid = self.env.company.partner_id.id

    @api.constrains('loan_rate_id')
    def _constrains_loan_rate_id(self):
        loan_agreement_stage_draft = self.env.ref('loan_base.loan_agreement_stage_draft',
                                                  raise_if_not_found=False)
        loan_agreement_stage_validated = self.env.ref('loan_base.loan_agreement_stage_validated',
                                                      raise_if_not_found=False)
        loan_agreement_stage_provided = self.env.ref('loan_base.loan_agreement_stage_provided',
                                                     raise_if_not_found=False)
        for agreement in self:
            today_date = fields.Date.today()

            # default values
            vals = agreement._get_rate_line_default_vals()

            # create loan rate line if not exist already.
            if not agreement.loan_rate_line_ids:
                agreement.loan_rate_line_ids = [(0, 0, vals)]

            last_rate_id = agreement.loan_rate_line_ids[-1:]

            # if rates changed
            if agreement.loan_rate_id.id != last_rate_id.rate_id.id:

                # case #1 - draft loan or validated loan
                if agreement.stage_id.id in (loan_agreement_stage_draft.id, loan_agreement_stage_validated.id):
                    agreement.loan_rate_line_ids = [(5, 0, 0),
                                                    (0, 0, vals)]
                # case #2 - loan in provided stage
                elif agreement.stage_id.id == loan_agreement_stage_provided.id:

                    # if current date equals date of line rate record
                    if self._date_as_tuple(last_rate_id.date_from) == self._date_as_tuple(today_date):
                        last_rate_id.rate_id = agreement.loan_rate_id.id

                    # if dates different
                    else:
                        # adds new line
                        agreement.loan_rate_line_ids = [(0, 0, vals)]
                        last_rate_id.date_to = fields.Date.to_string(today_date - relativedelta(days=1))
                else:
                    raise ValidationError(
                        _('Rate change in the status "{}" is prohibited'.format(_(agreement.stage_id.name))))

    @api.model
    def create(self, vals):
        if vals.get('loan_type') == 'payable':
            vals['borrower_company_pid'] = self.env.user.company_id.partner_id.id
        elif vals.get('loan_type') == 'receivable':
            vals['lender_company_pid'] = self.env.user.company_id.partner_id.id
        res = super().create(vals)
        return res

    def write(self, vals):
        if vals.get('loan_type') == 'payable':
            vals['borrower_company_pid'] = self.env.user.company_id.partner_id.id
        elif vals.get('loan_type') == 'receivable':
            vals['lender_company_pid'] = self.env.user.company_id.partner_id.id
        res = super().write(vals)
        return res

    # === CRUD methods (ORM overrides)
    def copy(self, default=None):
        self.ensure_one()
        default = {} if default is None else default
        default['name'] = self._default_name()
        return super().copy(default)

    # === Action methods

    # === Helper functions
    @staticmethod
    def _date_as_tuple(dt):
        if isinstance(dt, str):
            dt = fields.Date.to_date(dt)
        return dt.year, dt.month, dt.day

    # === And finally, other business methods.
    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        stage_ids = self.env['account.loan.agreement.stage'].search([])
        return stage_ids

    def get_days(self, date):
        """
        :return (day_in_month, day_in_year)
        """

        def actial_actual(dt):
            days_in_month = monthrange(dt.year, dt.month)[-1]
            days_in_year = 366 if isleap(dt.year) else 365
            return days_in_month, days_in_year

        self.ensure_one()
        get_days_count = {
            '30_360': lambda dt: (30, 360),
            '30_365': lambda dt: (30, 365),
            'actual_360': lambda dt: (actial_actual(dt)[0], 360),
            'actual_365': lambda dt: (actial_actual(dt)[0], 365),
            'actual_actual': actial_actual,
        }
        day_count_func = get_days_count[self.day_count_convention]
        days_in_month, days_in_year = day_count_func(date)
        return days_in_month, days_in_year

    def _create_activity(self, date=None, name=''):
        self.ensure_one()
        activity_type = self.env['mail.activity.type'].sudo().search([('category', '=', 'meeting')], limit=1)
        activity_id = self.env['mail.activity'].sudo().create({
            'res_model_id': self.env['ir.model'].search([('model', '=', 'account.loan.agreement')], limit=1).id,
            'res_id': self.id,
            'user_id': self.env.user.id,
            'activity_type_id': activity_type.id,
            'summary': name,
            'date_deadline': date,
        })
        calendar_event = self.env['calendar.event'].create({
            'name': name,
            'start': date,
            'start_date': fields.Date.to_string(date),
            'start_datetime': False,
            'stop': date,
            'stop_date': fields.Date.to_string(date),
            'stop_datetime': False,
            'allday': True,
            'activity_ids': [(6, False, activity_id.ids)],
            'res_model_id': self.env['ir.model'].search([('model', '=', 'account.loan.agreement')], limit=1).id,
            'res_id': self.id,
        })

    def create_activity(self, date=None, principal=0, interest=0):
        self.ensure_one()
        date = fields.Date.today() if date is None else date
        vals = dict(currency_name=self.loan_currency_id.name,
                    company_name=self.loan_type == 'receivable' and self.lender_company_pid.name or self.borrower_company_pid.name,
                    principal=principal,
                    interest=interest,
                    )
        activity_items = [(date, '{company_name}\nRepayment of Principal\n{principal:.2f} {currency_name}'),
                          (date, '{company_name}\nRepayment of Interest\n{interest:.2f} {currency_name}'),
                          ]
        for dt, name in activity_items:
            self._create_activity(dt, name.format(**vals))

    def get_rate_in_date(self, dt):
        self.ensure_one()
        dt = fields.Date.to_date(dt)
        # check if rate lines created

        agreement = self
        for date_from, date_to, rate_id in agreement.loan_rate_line_ids.mapped(
                lambda r: (r.date_from, r.date_to, r.rate_id)):
            if (fields.Date.to_date(date_from) <= dt <= fields.Date.to_date(date_to)) \
                    or fields.Date.to_date(date_from) <= fields.Date.to_date(dt) and not date_to:
                return rate_id.value
        return 0

    # === Buttons
    def button_create_activity(self):
        for agreement in self:
            # TODO: fix agreement.repayment_line_ids - нет доверия <Pavel 2019-03-27>
            for repayment_line in agreement.repayment_line_ids:
                date = repayment_line.date
                principal = repayment_line.principal
                interest = repayment_line.interest
                agreement.create_activity(date, principal, interest)

    def button_state_written_off(self):
        for agreement in self:
            agreement.stage_id = self.env.ref('loan_base.loan_agreement_stage_written_off',
                                              raise_if_not_found=False)

    def button_state_zeroed_out(self):
        for agreement in self:
            agreement.stage_id = self.env.ref('loan_base.loan_agreement_stage_zeroed_out',
                                              raise_if_not_found=False)

    def button_state_removed_from_computation(self):
        for agreement in self:
            agreement.stage_id = self.env.ref('loan_base.loan_agreement_stage_removed_from_computation',
                                              raise_if_not_found=False)

    def button_compute_table(self):
        for rec in self:
            prev_line = self.env['account.loan.agreement.payment.line']
            for line_number, line in enumerate(rec.payment_line_ids):

                if line_number == 0:
                    prev_date = fields.Date.to_date(line.date)
                    line.days = 0
                else:
                    curr_date = fields.Date.to_date(line.date)
                    line.days = (curr_date - prev_date).total_seconds() // 86400
                    prev_date = curr_date

                # other lines
                line._compute_accrual_in_loan_currency()
                line._compute_repayment_of_the_loan_body_in_the_loans_currency()
                line._compute_paid_interest_in_loan_currency()
                line._compute_loan_body_balance_in_loan_currency_beauty(prev_line)
                line._compute_accrued_interest_in_loan_currency(prev_line, line_number=line_number)
                line._compute_accrued_interest_in_company_currency()
                line._compute_exchange_difference_loan_body(prev_line)
                line._compute_loan_body_balance_in_company_currency(prev_line)
                line._compute_loan_body_balance_in_loan_currency()
                line._compute_interest_balance_in_loan_currency(prev_line)
                line._compute_loan_amount_in_loan_currency(prev_line)
                line._compute_loan_amount_in_company_currency()
                line._compute_interest_balance_in_company_currency(prev_line)
                line._compute_exchange_difference_loan_interest()

                # after_all
                prev_line = line

    def button_get_moves(self):
        account_move_line = self.env['account.move.line']
        for agreement in self:
            table = []
            agreement.payment_line_ids.unlink()
            for a_type, account_id in zip(('interest', 'principal'),
                                          (agreement.accrued_interest_account_id, agreement.loan_principal_account_id)):
                domain = [('account_id', '=', account_id.id), ('loan_agreement_id', '=', agreement.id)]
                move_lines = account_move_line.search(domain)
                filter_criteria_exchange_diff_reverse = lambda ml: 'exchange difference' not in str(
                    ml.name).lower() and 'reversal of' not in str(ml.display_name).lower() and not ml.reconciled
                move_lines_without_filtered_lines = move_lines.filtered(filter_criteria_exchange_diff_reverse)
                for move_line in move_lines_without_filtered_lines:
                    vals = {
                        'account_type': a_type,
                        'date': FILTERED_DATE if move_line.date < FILTERED_DATE else move_line.date,
                        'debit': move_line.debit,
                        'credit': move_line.credit,
                        'payment_currency': move_line.currency_id.id or agreement.company_currency_id.id,
                        'amount_currency_debit': move_line.amount_currency if move_line.amount_currency > 0 else 0,
                        'amount_currency_credit': -move_line.amount_currency if move_line.amount_currency < 0 else 0,
                    }
                    table.append(vals)
            if table:
                df = DataFrame(table)
                aggfunc = {
                    'debit': np.sum,
                    'credit': np.sum,
                    'amount_currency_debit': np.sum,
                    'amount_currency_credit': np.sum,
                }
                table_keys = [
                    'debit',
                    'credit',
                    'amount_currency_debit',
                    'amount_currency_credit',
                ]
                pd_table = pivot_table(df, values=table_keys,
                                       index=['date', 'account_type', 'payment_currency'], aggfunc=aggfunc)
                result_table = {}
                for keys, value in pd_table.to_dict('index').items():
                    date, account_type, payment_currency = keys
                    result_table[date] = result_table.get(date, defaultdict(int))
                    result_table[date]['{}_debit'.format(account_type)] += value['debit']
                    result_table[date]['{}_credit'.format(account_type)] += value['credit']
                    result_table[date]['payment_currency'] = payment_currency

                    agreement_company_currency_id = agreement.company_currency_id
                    payment_currency_id = self.env['res.currency'].browse(payment_currency)
                    rate = payment_currency_id.with_context(date=date)

                    amount_currency_debit = value['amount_currency_debit']
                    amount_currency_credit = value['amount_currency_credit']
                    result_table[date]['{}_amount_currency_debit'.format(account_type)] += rate.compute(
                        amount_currency_debit, agreement_company_currency_id, round=False)
                    result_table[date]['{}_amount_currency_credit'.format(account_type)] += rate.compute(
                        amount_currency_credit, agreement_company_currency_id, round=False)

                first_accrual_date = False
                for date, value in sorted(result_table.items(), key=itemgetter(0)):
                    payment_currency = value.get('payment_currency', 0) or agreement.company_currency_id.id

                    # course compute
                    loan_currency_id = agreement.loan_currency_id
                    agreement_company_currency_id = agreement.company_currency_id
                    rate = agreement_company_currency_id.with_context(date=date)
                    course2 = rate.compute(1, loan_currency_id, round=False)

                    vals = {'date': date,
                            'payment_currency': payment_currency,
                            'course1': 1,
                            'course2': course2,
                            'line_type': 'move',
                            }
                    interest_debit = value.get('interest_debit', 0)
                    principal_debit = value.get('principal_debit', 0)
                    interest_credit = value.get('interest_credit', 0)
                    principal_credit = value.get('principal_credit', 0)

                    if not self.is_receivable:
                        # if payable swap debit with credit
                        interest_debit, interest_credit = interest_credit, interest_debit
                        principal_debit, principal_credit = principal_credit, principal_debit

                    if principal_debit > 0:
                        first_accrual_date = first_accrual_date if first_accrual_date else agreement.set_drawdown_date(
                            date)
                        vals['accrual_in_company_currency'] = principal_debit
                    if principal_credit > 0:
                        vals['repayment_of_the_loan_body_in_the_company_currency'] = -principal_credit
                    if interest_debit > 0:
                        vals['accrued_interest_fact_in_company_currency'] = interest_debit
                        vals['accrued_interest_in_company_currency'] = interest_debit
                    if interest_credit > 0:
                        vals['paid_interest_in_company_currency'] = -interest_credit

                    agreement.payment_line_ids = [(0, 0, vals)]

            agreement.button_compute_table()

    def set_drawdown_date(self, drawdown_date):
        self.ensure_one()
        self.drawdown_date = drawdown_date
        self.loan_rate_line_ids[:1].date_from = drawdown_date
        return drawdown_date

    @staticmethod
    def _get_end_of_month_dates(dtstart=None, until=None):
        """
        :return: list of datetime
        """
        dtstart = datetime(2014, 12, 31) if dtstart is None else dtstart  # type: datetime
        until = datetime(2014, 12, 31) if until is None else until  # type: datetime
        dtstart, until = map(fields.Date.to_date, (dtstart, until))
        dates = list(rrule(freq=DAILY, dtstart=dtstart, until=until))
        dates = [d for d in dates if d.day == monthrange(d.year, d.month)[-1]]
        return dates

    def button_lunch_entries_posting_period(self):
        loan_agreement_stage_provided = self.env.ref('loan_base.loan_agreement_stage_provided',
                                                     raise_if_not_found=False)
        for agreement in self:
            # only for provided loan agreements
            if agreement.stage_id.id != loan_agreement_stage_provided.id:
                continue

            today = fields.Date.today()
            if not agreement.entries_posting_period_from or not agreement.entries_posting_period_to:
                ValidationError(_(
                    '`Entries Posting Period From` and `Entries Posting Period To`'
                    ' Must be fulled before `Posting Entries`'))

            # Check and correct entries posting period range
            if agreement.entries_posting_period_from < agreement.drawdown_date:
                agreement.entries_posting_period_from = agreement.drawdown_date
            if agreement.entries_posting_period_to > today:
                agreement.entries_posting_period_to = today
            dtstart = agreement.entries_posting_period_from
            until = agreement.entries_posting_period_to
            agreement.with_context(no_recalc_entries_posting=True).lunch_entries_posting_period(dtstart=dtstart,
                                                                                                until=until)

    def lunch_entries_posting_period(self, dtstart=None, until=None):
        """ Общая функция для проведения проводок по процентам и курсовым разницам.
        :param dtstart: Date start (agreement.drawdown_date by default)
        :type dtstart: str
        :param until: date end (today by default)
        :type until: str
        :return:
        """
        self.ensure_one()
        agreement = self
        if dtstart is None:
            dtstart = agreement.drawdown_date
        if until is None:
            until = fields.Date.today()

        # agreement.button_get_moves()

        dates = self._get_end_of_month_dates(dtstart, until)
        dates_of_rate_changes = agreement.loan_rate_line_ids.mapped('date_from')
        payments_dates = [line.date for line in agreement.payment_line_ids]
        dates = sorted(set(map(fields.Date.to_date, dates + dates_of_rate_changes + payments_dates)))
        for date in dates:
            # course compute
            loan_currency_id = agreement.loan_currency_id
            user_company_currency_id = agreement.company_currency_id
            rate = user_company_currency_id.with_context(date=date)
            course2 = rate.compute(1, loan_currency_id, round=False)
            vals = {
                'priority': 20,
                'date': fields.Date.to_string(date),
                'course1': 1,
                'course2': course2,
                'line_type': 'calc'}
            agreement.payment_line_ids = [(0, 0, vals)]

        agreement.button_compute_table()

        def filter_payment_lines(payment_line_ids):
            for pl in payment_line_ids:
                if pl.date < FILTERED_DATE:
                    continue
                is_calc_and_accrued_interest_in_company_currency = (
                        pl.line_type == 'calc' and pl.accrued_interest_in_company_currency > 0)
                is_move_and_not_accrued_interest_fact_in_company_currency = (
                        pl.line_type == 'move' and pl.accrued_interest_fact_in_company_currency == 0)
                if is_calc_and_accrued_interest_in_company_currency or \
                        is_move_and_not_accrued_interest_fact_in_company_currency:
                    yield pl

        for payment_line in filter_payment_lines(agreement.payment_line_ids):
            move_date = payment_line.date

            agreement._phase_1(payment_line, move_date)
            agreement.button_compute_table()
            agreement._phase_2(payment_line, move_date)
            agreement.button_compute_table()

        agreement.button_get_moves()
        return True

    def _phase_1(self, payment_line, move_date):
        """ Фаза 1 проводка начисленных процентов
        :type move_date: str
        :param payment_line:
        :return: None
        """
        self.ensure_one()
        agreement = self
        Move = self.env['account.move']
        accrued_interest_in_company_currency = payment_line.accrued_interest_in_company_currency
        if agreement.is_receivable:
            sign = 1
            debit_move1, credit_move1 = (0, accrued_interest_in_company_currency)
            move1_account_id = agreement.interest_receivable_account_id.id
        else:
            sign = -1
            debit_move1, credit_move1 = (accrued_interest_in_company_currency, 0)
            move1_account_id = agreement.interest_payable_account_id.id
        debit_move2, credit_move2 = credit_move1, debit_move1
        move1_amount_currency = -payment_line.accrued_interest_in_loan_currency * sign
        move2_amount_currency = -move1_amount_currency
        move2_account_id = agreement.accrued_interest_account_id.id
        move_currency_id = agreement.loan_currency_id
        move_vals = {
            'loan_agreement_id': agreement.id,
            'journal_id': agreement.transactions_journal_id.id,
            'date': move_date,
            'ref': 'Accrual of interest {} {}'.format(agreement.name, move_date),
            'line_ids': [
                (0, 0, {
                    'name': 'Accrual of interest {} {}'.format(agreement.name, move_date),
                    'date': move_date,
                    'amount_currency': move1_amount_currency,
                    'debit': debit_move1,
                    'credit': credit_move1,
                    'currency_id': move_currency_id.id,
                    'account_id': move1_account_id,
                    'loan_agreement_id': agreement.id,
                }),
                (0, 0, {
                    'name': 'Accrual of interest {} {}'.format(agreement.name, move_date),
                    'date': move_date,
                    'amount_currency': move2_amount_currency,
                    'debit': debit_move2,
                    'credit': credit_move2,
                    'currency_id': move_currency_id.id,
                    'account_id': move2_account_id,
                    'loan_agreement_id': agreement.id,
                })]
        }
        if abs(credit_move1) > MOVE_THRESHOLD or abs(debit_move1) > MOVE_THRESHOLD:
            Move.with_context(check_move_validity=False).create(move_vals)

    def _phase_2(self, payment_line, move_date):
        """ Фаза 2 проводка курсовых разниц.
        :type move_date: str
        :param payment_line:
        :return: None
        """
        self.ensure_one()
        agreement = self
        move = self.env['account.move']

        # Подготовка
        move3_account_id = agreement.loan_principal_account_id
        move5_account_id = agreement.accrued_interest_account_id
        principal_exchange_diff_amount = payment_line.exchange_difference_loan_body
        interest_exchange_diff_amount = payment_line.exchange_difference_loan_interest
        if agreement.is_receivable:
            if principal_exchange_diff_amount > 0:
                debit_move3, credit_move3 = (abs(principal_exchange_diff_amount), 0)
                move4_account_id = agreement.unr_exchange_gain_account_id
            else:
                debit_move3, credit_move3 = (0, abs(principal_exchange_diff_amount))
                move4_account_id = agreement.unr_exchange_loss_account_id
            debit_move4, credit_move4 = credit_move3, debit_move3
            move3_amount = principal_exchange_diff_amount
            move4_amount = -principal_exchange_diff_amount

            if interest_exchange_diff_amount > 0:
                debit_move5, credit_move5 = (abs(interest_exchange_diff_amount), 0)
                move6_account_id = agreement.unr_exchange_gain_account_id
            else:
                debit_move5, credit_move5 = (0, abs(interest_exchange_diff_amount))
                move6_account_id = agreement.unr_exchange_loss_account_id
            debit_move6, credit_move6 = credit_move5, debit_move5
            move5_amount = interest_exchange_diff_amount
            move6_amount = -interest_exchange_diff_amount
            company_partner_id = agreement.borrower_company_pid.id
        else:
            if principal_exchange_diff_amount > 0:
                debit_move3, credit_move3 = (0, abs(principal_exchange_diff_amount))
                move4_account_id = agreement.unr_exchange_loss_account_id
            else:
                debit_move3, credit_move3 = (abs(principal_exchange_diff_amount), 0)
                move4_account_id = agreement.unr_exchange_gain_account_id
            debit_move4, credit_move4 = credit_move3, debit_move3
            move3_amount = -principal_exchange_diff_amount
            move4_amount = principal_exchange_diff_amount

            if interest_exchange_diff_amount > 0:
                debit_move5, credit_move5 = (0, abs(interest_exchange_diff_amount))
                move6_account_id = agreement.unr_exchange_loss_account_id
            else:
                debit_move5, credit_move5 = (abs(interest_exchange_diff_amount), 0)
                move6_account_id = agreement.unr_exchange_gain_account_id
            debit_move6, credit_move6 = credit_move5, debit_move5
            move5_amount = -interest_exchange_diff_amount
            move6_amount = interest_exchange_diff_amount
            company_partner_id = agreement.lender_company_pid.id

        # Фаза 2.1 проводка курсовых разниц по телу займа.
        _logger.info('phase 2.1')
        transactions_journal_id = agreement.unr_exchange_gain_loss_journal_id.id or agreement.transactions_journal_id.id
        move_vals34 = {
            'loan_agreement_id': agreement.id,
            'journal_id': transactions_journal_id,
            'date': move_date,
            'ref': 'Exchange difference of principal {} {}'.format(agreement.name, move_date),
            'line_ids': [(0, 0, {
                'name': 'Exchange difference of principal {} {}'.format(agreement.name, move_date),
                'date': move_date,
                'amount_currency': move3_amount,
                'debit': debit_move3,
                'credit': credit_move3,
                'currency_id': agreement.company_currency_id.id,
                'account_id': move3_account_id.id,
                'loan_agreement_id': agreement.id,
                'partner_id': company_partner_id,
            }), (0, 0, {
                'name': 'Exchange difference of principal {} {}'.format(agreement.name, move_date),
                'date': move_date,
                'amount_currency': move4_amount,
                'debit': debit_move4,
                'credit': credit_move4,
                'currency_id': agreement.company_currency_id.id,
                'account_id': move4_account_id.id,
                'loan_agreement_id': agreement.id,
                'partner_id': company_partner_id,
            })]
        }
        if abs(credit_move3) > MOVE_THRESHOLD or abs(debit_move3) > MOVE_THRESHOLD:
            if not move.search([('loan_agreement_id', '=', agreement.id), ('date', '=', move_date),
                                ('ref', 'ilike', 'Exchange difference of principal')]):
                move = move.create(move_vals34)

        # Фаза 2.2 проводка курсовых разниц по процентам займа.
        _logger.info('phase 2.2')
        move_vals56 = {
            'loan_agreement_id': agreement.id,
            'journal_id': transactions_journal_id,
            'date': move_date,
            'ref': 'Exchange difference of interest {} {}'.format(agreement.name, move_date),
            'line_ids': [(0, 0, {
                'name': 'Exchange difference of interest {} {}'.format(agreement.name, move_date),
                'date': move_date,
                'amount_currency': move5_amount,
                'debit': debit_move5,
                'credit': credit_move5,
                'currency_id': agreement.company_currency_id.id,
                'account_id': move5_account_id.id,
                'loan_agreement_id': agreement.id,
                'partner_id': company_partner_id,
            }), (0, 0, {
                'name': 'Exchange difference of interest {} {}'.format(agreement.name, move_date),
                'date': move_date,
                'amount_currency': move6_amount,
                'debit': debit_move6,
                'credit': credit_move6,
                'currency_id': agreement.company_currency_id.id,
                'account_id': move6_account_id.id,
                'loan_agreement_id': agreement.id,
                'partner_id': company_partner_id,
            })]
        }
        if abs(credit_move5) > MOVE_THRESHOLD or abs(debit_move5) > MOVE_THRESHOLD:
            if not move.search([('loan_agreement_id', '=', agreement.id), ('date', '=', move_date),
                                ('ref', 'ilike', 'Exchange difference of interest')]):
                move.with_context(check_move_validity=False).create(move_vals56)

    def button_state_validated(self):
        account_reconcile_model = self.env['account.reconcile.model']
        loan_agreement_stage_validated = self.env.ref('loan_base.loan_agreement_stage_validated',
                                                      raise_if_not_found=False)
        for agreement in self:
            # TODO: check the logic below <Pavel 2019-04-25>
            is_create_opposite_loan = False
            if agreement._get_opposite_company_id().create_la_when_lending_to_this_company and agreement.loan_type == 'receivable':
                is_create_opposite_loan = True
            elif agreement._get_opposite_company_id().create_la_when_borrow_from_this_company and agreement.loan_type == 'payable':
                is_create_opposite_loan = True

            if not agreement.opposite_loan_agreement_id and is_create_opposite_loan:
                opposite_loan_type = 'payable' if agreement.loan_type == 'receivable' else 'payable'
                opposite_loan_agreement_id = agreement.sudo().copy(default={
                    'opposite_loan_agreement_id': agreement.id,
                    'loan_type': opposite_loan_type,
                })
                opposite_loan_agreement_id.borrower_company_pid = agreement.borrower_company_pid.id
                opposite_loan_agreement_id.lender_company_pid = agreement.lender_company_pid.id

                agreement.opposite_loan_agreement_id = opposite_loan_agreement_id.id
                opposite_loan_agreement_id.button_create_accounts()

            agreement.button_create_accounts()
            if not agreement.rule_id:
                agreement.rule_id = account_reconcile_model.create_rule_for_loan(agreement_id=agreement).id
            agreement.stage_id = loan_agreement_stage_validated.id

    def button_state_provided(self):
        for agreement in self:
            agreement.stage_id = self.env.ref('loan_base.loan_agreement_stage_provided',
                                              raise_if_not_found=False)

    def _get_company_id(self):
        self.ensure_one()
        if self.loan_type == 'receivable':
            company_pid = self.lender_company_pid
        elif self.loan_type == 'payable':
            company_pid = self.borrower_company_pid
        else:
            company_pid = self.env['res.partner']
        result = company_pid.company_id or self.env['res.company']
        return result

    def _get_opposite_company_id(self):
        self.ensure_one()
        if self.loan_type == 'receivable':
            company_pid = self.borrower_company_pid
        elif self.loan_type == 'payable':
            company_pid = self.lender_company_pid
        else:
            company_pid = self.env['res.partner']
        result = company_pid.company_id or self.env['res.company']
        return result

    def button_create_accounts(self):
        current_liabilities = self.env.ref('account.data_account_type_current_liabilities', raise_if_not_found=False)
        cost_of_revenue = self.env.ref('account.data_account_type_direct_costs', raise_if_not_found=False)
        non_current_assets = self.env.ref('account.data_account_type_non_current_assets', raise_if_not_found=False)
        receivable_accounts = [
            ('Loan {loan_name}', 'LB{loan_name}', non_current_assets, 'loan_principal_account_id'),
            ('Interest on Loan {loan_name}', 'IL{loan_name}', non_current_assets, 'accrued_interest_account_id'),
            ('Interest Receivable {loan_name}', 'IR{loan_name}', cost_of_revenue, 'interest_receivable_account_id'),
        ]
        payable_accounts = [
            ('Loan {loan_name}', 'LB{loan_name}', current_liabilities, 'loan_principal_account_id'),
            ('Interest on Loan {loan_name}', 'IL{loan_name}', current_liabilities, 'accrued_interest_account_id'),
            ('Interest Payable {loan_name}', 'IP{loan_name}', cost_of_revenue, 'interest_payable_account_id'),
        ]

        accounts = receivable_accounts
        for agreement in self:
            agreement_name_without_spaces = agreement.name.replace(' ', '')
            company = agreement._get_company_id()
            if agreement.loan_type == 'payable':
                accounts = payable_accounts
            elif agreement.loan_type == 'receivable':
                accounts = receivable_accounts
            for account_name, account_code, account_type, agreement_field_name in accounts:
                if not getattr(agreement, agreement_field_name, None):
                    account_id = self.env['account.account'].create({
                        'name': account_name.format(loan_name=agreement_name_without_spaces),
                        'code': account_code.format(loan_name=agreement_name_without_spaces),
                        'user_type_id': account_type.id,
                        'company_id': company.id,
                    })
                    setattr(agreement, agreement_field_name, account_id.id)

    def _get_rate_line_default_vals(self, date_from=None):
        date_from = fields.Date.today() if date_from is None else date_from
        self.ensure_one()
        agreement = self
        vals = {'date_from': date_from,
                'agreement_id': agreement.id,
                'rate_id': agreement.loan_rate_id.id}
        return vals

    def set_state_provided(self):
        loan_agreement_stage_provided = self.env.ref('loan_base.loan_agreement_stage_provided',
                                                     raise_if_not_found=False)

        for agreement in self:
            agreement.stage_id = loan_agreement_stage_provided.id
            # Fixing date of provided loan in `drawdown_date` field.
            agreement.drawdown_date = fields.Date.today()
            vals = agreement._get_rate_line_default_vals(date_from=agreement.drawdown_date)
            agreement.loan_rate_line_ids = [([(0, 0, vals)])]

    def set_state_repaid(self):
        loan_agreement_stage_repaid = self.env.ref('loan_base.loan_agreement_stage_repaid',
                                                   raise_if_not_found=False)
        for agreement in self:
            agreement.stage_id = loan_agreement_stage_repaid.id

    def button_constrains_loan_agreement_id(self):
        move_line_ids = self.env['account.move'].sudo().search([])
        move_line_ids._constrain_line_ids()

    def get_interest_principal_on_date_by_balance(self, dt, balance, amount_type):
        self.ensure_one()
        agreement_id = self
        # Compute interest value on date.
        agreement_id.interest_accrual_date_type = 'custom'
        agreement_id.interest_accrual_date_custom = dt
        agreement_id.button_compute_interest_outstanding_on_date()

        # TODO: add currency rate conversation <Pavel 2019-04-26>
        interest_outstanding_on_date = agreement_id.interest_outstanding_on_date
        principal_outstanding_on_date = agreement_id.principal_outstanding_on_date

        # interest_outstanding_on_date

        if amount_type == 'interest_first_principal_second':
            line1_balance = min([balance, interest_outstanding_on_date])
            line2_balance = min([balance - line1_balance, principal_outstanding_on_date])
        else:
            line2_balance = min([balance, principal_outstanding_on_date])
            line1_balance = min([balance - line2_balance, interest_outstanding_on_date])

        return line1_balance, line2_balance

    def button_check_constrains_loan_agreement_id(self):
        for agreement_id in self:
            for move_line_id in agreement_id.move_ids.mapped('line_ids').sorted('date', reverse=True)[-1:]:
                _logger.info('move line with date {} constrain'.format(move_line_id.date))
                move_line_id.constrains_loan_agreement_id()

    def button_get_principal_interest_amount(self):
        for agreement_id in self:
            loan_principal_account_id = agreement_id and agreement_id.loan_principal_account_id
            accrued_interest_account_id = agreement_id and agreement_id.accrued_interest_account_id
            agreement_id.current_principal = loan_principal_account_id.get_balance(loan_agreement_id=agreement_id, )
            agreement_id.current_interest = accrued_interest_account_id.get_balance(loan_agreement_id=agreement_id, )
