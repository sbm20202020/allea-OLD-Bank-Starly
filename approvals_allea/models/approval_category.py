from odoo import fields, models


CREATED_DOCUMENT_SELECTION = [
    ('purchase_order', 'Purchase Order')]


class ApprovalCategory(models.Model):
    _inherit = 'approval.category'

    create_document = fields.Selection(CREATED_DOCUMENT_SELECTION, string='Created Document')
