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
from odoo import models, fields, api, _


# === Imports from odoo addons ===
# from odoo.addons.website.models.website import slug

# === Local application imports ==
# from ..exceptions import BaseModuleNameError

# === CONSTANTS ==================
# SPEED_OF_LIGHT_M_S = 299792458

# === Module init variables ======
# myvar = 'test'


class ProductProduct(models.Model):
    """Product Product"""
    # - In a Model attribute order should be
    # === Private attributes (``_name``, ``_description``, ``_inherit``, ...)
    _inherit = "product.product"  # the model name
    # === Default method and ``_default_get``
    # === Field declarations
    # === Compute, inverse and search methods in the same order as field declaration
    # === Selection method (methods used to return computed values for selection fields)
    # === Constrains methods (``@api.constrains``) and onchange methods (``@api.onchange``)
    # === CRUD methods (ORM overrides)
    # === Action methods
    # === And finally, other business methods.

    # === OVERRIDE
    @api.model
    def _convert_prepared_anglosaxon_line(self, line, partner):
        result = super()._convert_prepared_anglosaxon_line(line, partner)
        invoice_line_id = line.get('invl_id', 0)
        result['invoice_line_id'] = invoice_line_id
        invoice_tax_line_id = line.get('invoice_tax_line_id', 0)
        result['invoice_tax_line_id'] = invoice_tax_line_id
        return result
