"""
Module is designed taking into account the odoo guidelines:
  `https://www.odoo.com/documentation/12.0/reference/guidelines.html`
"""
# === Standard library imports ===
import logging

# === Init logger ================
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

# === Third party imports ========
# import pandas

# === Imports of odoo ============
from odoo import models, fields, api, _  # noqa: F401 #pylint: disable=W0611


# === Imports from odoo addons ===
# from odoo.addons.website.models.website import slug

# === Local application imports ==
# from ..exceptions import BaseModuleNameError

# === CONSTANTS ==================
# SPEED_OF_LIGHT_M_S = 299792458

# === Module init variables ======
# myvar = 'test'


class AccountMoveLine(models.Model):
    """AccountMoveLine"""
    # - In a Model attribute order should be
    # === Private attributes (``_name``, ``_description``, ``_inherit``, ...)
    _inherit = 'account.move.line'  # the model name
    # === Default method and ``_default_get``
    # === Field declarations
    # === Compute, inverse and search methods in the same order as field declaration
    # === Selection method (methods used to return computed values for selection fields)
    # === Constrains methods (``@api.constrains``) and onchange methods (``@api.onchange``)
    # === CRUD methods (ORM overrides)
    # === Action methods
    # === And finally, other business methods.

    @api.constrains('analytic_tag_ids')
    def constrains_analytic_tag_ids(self):
        AccountInvoice = self.env['account.move']
        class_dict = AccountInvoice.get_class_dict()
        for move_line_id in self:
            move_id = move_line_id.move_id
            analytic_tag_ids = move_line_id.analytic_tag_ids
            matched_analytic_tag_ids = [tag_id for tag_id in analytic_tag_ids if tag_id in class_dict]
            if len(matched_analytic_tag_ids) > 1:
                raise ValidationError(
                    _('For move line `{}` must be only one VAT analytic tag!').format(move_id.name))
