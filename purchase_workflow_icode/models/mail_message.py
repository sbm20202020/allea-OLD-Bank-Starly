from odoo import models, api  # noqa: F401 #pylint: disable=W0611


class Message(models.Model):
    """Message"""

    _inherit = "mail.message"  # the model name

    @api.model
    def create(self, values):
        result = super().create(values)
        if not self.env.context.get('duplicate'):
            model = values.get('model')
            if model == 'purchase.order':
                purchase_order_id = values.get('res_id')
                if purchase_order_id:
                    invoice_ids = self.env['purchase.order'].browse(purchase_order_id).invoice_ids.ids
                    account_invoice_ids = self.env['account.move'].browse(invoice_ids).ids
                    for account_invoice_id in account_invoice_ids:
                        values['model'] = 'account.move'
                        values['res_id'] = account_invoice_id
                        self.env['mail.message'].with_context(duplicate=True).create(values)
            if model == 'account.move':
                account_invoice_id = values.get('res_id')
                purchase_id = self.env['purchase.order'].search([('invoice_ids', 'in', [account_invoice_id])]).id
                if purchase_id:
                    values['model'] = 'purchase.order'
                    values['res_id'] = purchase_id
                    self.env['mail.message'].with_context(duplicate=True).create(values)
        return result
