from odoo import models, api


class IrAttachment(models.Model):
    """Attachment"""

    _inherit = "ir.attachment"

    @api.model
    def create(self, values):
        result = super().create(values)
        if not self.env.context.get('duplicate'):
            res_model = values.get('res_model')
            if res_model == 'purchase.order':
                purchase_order_id = values.get('res_id')
                if purchase_order_id:
                    invoice_ids = self.env['purchase.order'].browse(purchase_order_id).invoice_ids.ids
                    account_invoice_ids = self.env['account.move'].browse(invoice_ids).ids
                    for account_invoice_id in account_invoice_ids:
                        values['res_model'] = 'account.move'
                        values['res_id'] = account_invoice_id
                        self.env['ir.attachment'].with_context(duplicate=True).create(values)
            if res_model == 'account.move':
                account_invoice_id = values.get('res_id')
                purchase_id = self.env['purchase.order'].search([('invoice_ids', 'in', [account_invoice_id])]).id
                if purchase_id:
                    values['res_model'] = 'purchase.order'
                    values['res_id'] = purchase_id
                    self.env['ir.attachment'].with_context(duplicate=True).create(values)
        return result

    def unlink(self):
        result = super().unlink()
        return result
