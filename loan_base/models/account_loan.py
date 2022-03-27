from odoo import fields, models


class Loan(models.Model):
    """Loan"""

    _name = "account.loan"

    name = fields.Char('Name')
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id.id)
