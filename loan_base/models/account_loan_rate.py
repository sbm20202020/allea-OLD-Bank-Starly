from odoo import models, fields, api
from decimal import Decimal


class LoanRate(models.Model):
    """Loan Rate"""

    _name = 'account.loan.rate'

    name = fields.Char('Name')
    value = fields.Float('Value (%/100)', digits=(12, 6), default=0.01)  # percent/100

    @api.onchange('value')
    def _onchange_value(self):
        value = Decimal('{:.6f}'.format(self.value))
        self.name = '{}%'.format(self._remove_exponent(value*100))

    @staticmethod
    def _remove_exponent(d):
        return d.quantize(Decimal(1)) if d == d.to_integral() else d.normalize()
