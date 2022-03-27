from odoo import models, fields, api


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'
    agreement_id = fields.Many2one(related='order_id.agreement_id', string='Purchase Agreement')
