from odoo import models, fields, api


class PurchaseOrder(models.Model):
    """PurchaseOrder"""

    _inherit = 'purchase.order'

    name = fields.Char(string='Name', translate=True)
    account_invoice_state = fields.Selection(related='invoice_ids.state', string='Vendor Bill Status', default=False)
    vendor_date = fields.Date(string='Vendor Date', states={'draft': [('readonly', False)]})
    state = fields.Selection([
        ('draft', 'RFQ'),
        ('sent', 'RFQ Sent'),
        ('to approve', 'To Approve'),
        ('purchase', 'Purchase Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
        ('sent to bank', 'Sent To Bank'),
        ('authorized', 'Authorized'),
        ('paid', 'Paid')
    ], string='Status', readonly=True, index=True, copy=False, default='draft', track_visibility='onchange')

    def button_sent_to_bank(self):
        self.write({'state': 'sent to bank'})
        return {}

    def button_authorized(self):
        self.write({'state': 'authorized'})
        return {}

    def button_paid(self):
        self.write({'state': 'paid'})
        return {}
