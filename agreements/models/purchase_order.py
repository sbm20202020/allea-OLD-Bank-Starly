from odoo import models, fields


class PurchaseOrder(models.Model):
    """PurchaseOrder"""
    _inherit = 'purchase.order'

    agreement_id = fields.Many2one('agreement', string='Purchase Agreement')
