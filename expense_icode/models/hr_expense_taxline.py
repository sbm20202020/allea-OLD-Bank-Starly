"""
Module is designed taking into account the odoo guidelines:
  `https://www.odoo.com/documentation/12.0/reference/guidelines.html`
"""
# === Standard library imports ===
import logging

# === Init logger ================
_logger = logging.getLogger(__name__)

# === Third party imports ========
# import pandas

# === Imports of odoo ============
from odoo import models, fields, api


# === Imports from odoo addons ===
# from odoo.addons.website.models.website import slug

# === Local application imports ==
# from ..exceptions import BaseModuleNameError


# === CONSTANTS ==================
# SPEED_OF_LIGHT_M_S = 299792458

# === Module init variables ======
# myvar = 'test'


class HrExpenseTaxline(models.Model):
    """Hr Expense Taxline"""
    # - In a Model attribute order should be
    # === Private attributes (``_name``, ``_description``, ``_inherit``, ...)
    _name = 'hr.expense.taxline'  # the model name
    _description = __doc__  # the model's informal name
    # === Default method and ``_default_get``
    # === Field declarations
    name = fields.Char(string='Tax Name', required=True, translate=True)
    account_id = fields.Many2one('account.account',
                                 string='Tax Account',
                                 help="Account that will be set on invoice tax lines for invoices."
                                      " Leave empty to use the expense account.")
    amount = fields.Float(required=True, digits=(16, 4))
    analytic = fields.Boolean(string="Include in Analytic Cost",
                              help="If set, the amount computed by this tax will be assigned to the same"
                                   " analytic account as the invoice line (if any)")
    base = fields.Float(required=True, digits=(16, 4))
    # id = fields.Integer()  # for reference only
    price_include = fields.Boolean(string='Included in Price', default=False,
                                   help="Check this if the price you use on the product"
                                        " and invoices includes this tax.")
    refund_account_id = fields.Many2one('account.account',
                                        string='Tax Account on Credit Notes',
                                        help="Account that will be set on invoice tax lines"
                                             " for credit notes. Leave empty to use the expense account.",)
    sequence = fields.Integer(required=True, default=1,
                              help="The sequence field is used to define order in which the tax lines are applied.")

    tax_exigibility = fields.Selection(
        [('on_invoice', 'Based on Invoice'),
         ('on_payment', 'Based on Payment'),
         ], string='Tax Due', default='on_invoice',
        help="Based on Invoice: the tax is due as soon as the invoice is validated.\n"
             "Based on Payment: the tax is due as soon as the payment of the invoice is received.")

    manual = fields.Boolean(default=False)

    expense_id = fields.Many2one('hr.expense')
    tax_id = fields.Many2one('account.tax')

    # === Compute, inverse and search methods in the same order as field declaration
    # === Selection method (methods used to return computed values for selection fields)

    # === Constrains methods (``@api.constrains``) and onchange methods (``@api.onchange``)

    # === CRUD methods (ORM overrides)
    # === Action methods

    # === And finally, other business methods.

    def get_dict(self):
        self.ensure_one()
        result = {'account_id': self.account_id.id,
                  'amount': self.amount,
                  'analytic': self.analytic,
                  'base': self.base,
                  'id': self.tax_id.id,
                  'name': self.name,
                  'price_include': self.price_include,
                  'refund_account_id': self.refund_account_id.id,
                  'sequence': self.sequence,
                  'tax_exigibility': self.tax_exigibility}
        return result
