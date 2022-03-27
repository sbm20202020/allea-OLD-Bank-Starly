from odoo import models, fields


class ResPartner(models.Model):
    """Partner"""

    _inherit = 'res.partner'

    is_lender = fields.Boolean('Is Lender', default=False)
    is_borrower = fields.Boolean('Is Borrower', default=False)
