from odoo import models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def action_view_invoice(self):
        result = super().action_view_invoice()
        result['context']['default_date'] = self.vendor_date
        result['context']['default_invoice_date'] = self.vendor_date
        result['context']['default_currency_id'] = self.currency_id.id
        return result
