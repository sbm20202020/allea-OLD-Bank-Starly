from odoo import models, fields


class AgreementType(models.Model):
    """AgreementType"""

    _name = 'agreement.type'  # the model name

    name = fields.Char(string='Name', translate=True)
