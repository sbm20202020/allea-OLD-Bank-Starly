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
from odoo import models, fields, api, _  # noqa: F401 #pylint: disable=W0611


# === Imports from odoo addons ===
# from odoo.addons.website.models.website import slug

# === Local application imports ==
# from ..exceptions import BaseModuleNameError

# === CONSTANTS ==================
# SPEED_OF_LIGHT_M_S = 299792458

# === Module init variables ======
# myvar = 'test'


class ResPartner(models.Model):
    """ResPartner"""
    # - In a Model attribute order should be
    # === Private attributes (``_name``, ``_description``, ``_inherit``, ...)
    _inherit = 'res.partner'  # the model name
    # === Default method and ``_default_get``
    # === Field declarations
    is_in_eu = fields.Boolean(related='country_id.is_in_eu')
    # === Compute, inverse and search methods in the same order as field declaration
    # === Selection method (methods used to return computed values for selection fields)
    # === Constrains methods (``@api.constrains``) and onchange methods (``@api.onchange``)
    # === CRUD methods (ORM overrides)
    # === Action methods
    # === And finally, other business methods.
