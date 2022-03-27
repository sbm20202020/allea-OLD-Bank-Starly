from odoo import models, fields, api, _


class AccountAccountType(models.Model):
    _inherit = "account.account.type"
    sequence = fields.Integer(required=True, default=300,
                              help='Use to arrange type sequence')
    sequence_group = fields.Integer(required=True, default=10,
                                    help='Use to arrange type_group sequence')
