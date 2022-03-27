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
from odoo import models, fields, api, _, tools


# === Imports from odoo addons ===
# from odoo.addons.website.models.website import slug

# === Local application imports ==
# from ..exceptions import BaseModuleNameError

# === CONSTANTS ==================
# SPEED_OF_LIGHT_M_S = 299792458

# === Module init variables ======
# myvar = 'test'


class AccountMove(models.Model):
    """AccountMove"""
    # - In a Model attribute order should be
    # === Private attributes (``_name``, ``_description``, ``_inherit``, ...)
    _inherit = 'account.move'  # the model name
    # === Default method and ``_default_get``
    # === Field declarations
    # === Compute, inverse and search methods in the same order as field declaration
    # === Selection method (methods used to return computed values for selection fields)
    # === Constrains methods (``@api.constrains``) and onchange methods (``@api.onchange``)
    # === CRUD methods (ORM overrides)
    # === Action methods

    # === And finally, other business methods.
    def write_missing_invoice_line_id_in_move_lines(self):
        """env['account.invoice'].write_missing_invoice_line_id_in_move_lines(); env.cr.commit()"""
        AccountInvoice = self.sudo()
        invoice_ids = AccountInvoice or AccountInvoice.search([])
        for invoice_id in invoice_ids:
            move_id = invoice_id.move_id
            move_line_ids = move_id.line_ids
            for invoice_line_id in invoice_id.invoice_line_ids:
                def criteria_func(ml_id):
                    compare_slice = slice(None, 64)
                    ml_id_name = ml_id.name
                    invoice_line_id_name_first_line = invoice_line_id.name.splitlines(False)[0]
                    is_name_the_same = ml_id_name[compare_slice] == invoice_line_id_name_first_line[compare_slice]
                    is_account_id_the_same = ml_id.account_id.id == invoice_line_id.account_id.id
                    ml_id_amount = abs(ml_id.debit - ml_id.credit)
                    is_amount_the_same = tools.float_compare(ml_id_amount, invoice_line_id.price_subtotal,
                                                             precision_digits=2) == 0
                    ml_id_amount_currency = abs(ml_id.amount_currency)
                    is_amount_currency_the_same = all(
                        [ml_id_amount_currency > 0,
                         tools.float_compare(ml_id.amount_currency, invoice_line_id.price_subtotal,
                                             precision_digits=2) == 0])
                    return all([is_name_the_same,
                                is_account_id_the_same,
                                is_amount_the_same or is_amount_currency_the_same,
                                ])
                matched_move_line_ids = move_line_ids.filtered(criteria_func)
                matched_move_line_id = matched_move_line_ids[:1]
                if matched_move_line_id and not matched_move_line_id.invoice_line_id:
                    matched_move_line_id.invoice_line_id = invoice_line_id.id
                    matched_move_line_id.is_invoice_line_id_matched = True
