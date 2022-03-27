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
from odoo import models, api, tools, _  # noqa: F401 #pylint: disable=W0611
from odoo.exceptions import UserError

# === Imports from odoo addons ===
# from odoo.addons.website.models.website import slug

# === Local application imports ==
# from ..exceptions import BaseModuleNameError

# === CONSTANTS ==================
# SPEED_OF_LIGHT_M_S = 299792458

# === Module init variables ======
# myvar = 'test'


class Message(models.Model):
    # - In a Model attribute order should be
    # === Private attributes (``_name``, ``_description``, ``_inherit``, ...)
    _inherit = "mail.message"
    # === Default method and ``_default_get``

    @api.model
    def _get_default_from(self):
        mail_server = self.env['ir.mail_server'].sudo().search([], order='sequence', limit=1)
        if mail_server:
            return tools.formataddr((self.env.user.name, mail_server.smtp_user))

        # region origin
        if self.env.user.email:
            return tools.formataddr((self.env.user.name, self.env.user.email))

        raise UserError(_("Unable to send email, please configure the sender's email address."))
        # endregion

    @api.model
    def create(self, values):
        if values.get('message_type', False) == 'email':
            values.pop('email_from')
        return super().create(values)

    # === Field declarations
    # === Compute, inverse and search methods in the same order as field declaration
    # === Selection method (methods used to return computed values for selection fields)
    # === Constrains methods (``@api.constrains``) and onchange methods (``@api.onchange``)
    # === CRUD methods (ORM overrides)
    # === Action methods
    # === And finally, other business methods.
