from odoo import models, fields


class AccountLoanRateLine(models.Model):
    """AccountLoanRateLine"""

    _name = 'account.loan.rate.line'

    agreement_id = fields.Many2one('account.loan.agreement', string='Agreement')
    rate_id = fields.Many2one('account.loan.rate', string='Rate', required=True)
    state = fields.Selection([('draft', 'Draft'), ('validated', 'Validated')], string='State', default='draft')
    date_from = fields.Date('Date From', required=True,
                            states={'draft': [('readonly', False)], 'validated': [('readonly', True)]})
    date_to = fields.Date('Date To', states={'draft': [('readonly', False)], 'validated': [('readonly', True)]})

    _sql_constraints = [
        ('date_from_uniq', 'unique (agreement_id, date_from)', 'The `date from` for loan agreement must be unique!'),
        ('date_to_uniq', 'unique (agreement_id, date_to)', 'The `date to` for loan agreement must be unique!'),
    ]

    def filtered_by_date(self, dt=None):
        today = fields.Date.today()

        def filter_func(r):
            date_from = r.date_from
            date_to = r.date_to or today
            return date_from <= dt <= date_to

        return self.filtered(filter_func)

    def filtered_by_date_and_return_rate_value(self, dt=None):
        rate_id = self.filtered_by_date_and_return_rate_id(dt=dt)
        return rate_id.value or 0

    def filtered_by_date_and_return_rate_id(self, dt=None):
        rate_line = self.filtered_by_date(dt=dt)[:1]
        return rate_line.rate_id
