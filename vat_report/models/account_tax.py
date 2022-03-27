from odoo import models, fields


class AccountTax(models.Model):
    """Account Tax"""

    _inherit = "account.tax"

    is_standard = fields.Boolean(string='Standard Tax')
