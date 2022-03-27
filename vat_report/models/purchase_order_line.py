from odoo import models


class PurchaseOrderLine(models.Model):
    """Purchase Order Line"""

    _inherit = "purchase.order.line"

    def _compute_tax_id(self):
        for line in self:
            fpos = line.order_id.fiscal_position_id or line.order_id.partner_id.with_context(
                force_company=line.company_id.id).property_account_position_id
            # If company_id is set, always filter taxes by the company
            taxes = line.taxes_id._origin
            line.taxes_id = fpos.map_tax(taxes, line.product_id, line.order_id.partner_id) if fpos else taxes
