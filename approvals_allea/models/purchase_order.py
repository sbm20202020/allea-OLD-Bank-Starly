from odoo import models, fields


class PurchaseOrder(models.Model):
    """PurchaseOrder"""

    _inherit = 'purchase.order'

    account_invoice_state = fields.Selection(related='invoice_ids.state', string='Vendor Bill Status', default=False)
    approval_request_id = fields.Many2one('approval.request', string='Related Approval Request', ondelete='restrict')
    state = fields.Selection(selection_add=[
        ('draft', 'RFQ'),
        ('sent', 'RFQ Sent'),
        ('to approve', 'To Approve'),
        ('purchase', 'NEW'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
        ('investigation', 'Under Investigation'),
        ('sent to bank', 'Sent To Bank'),
        ('authorized', 'Authorized'),
        ('paid', 'Paid')
    ], string='Status', readonly=True, index=True, copy=False, default='draft', track_visibility='onchange')
    vendor_date = fields.Date(string='Vendor Date', states={'draft': [('readonly', False)]})

    def button_investigation(self):
        self.write({'state': 'investigation'})

    def button_sent_to_bank(self):
        self.write({'state': 'sent to bank'})

    def button_authorized(self):
        self.write({'state': 'authorized'})

    def button_paid(self):
        self.write({'state': 'paid'})

    def button_new(self):
        self.write({'state': 'purchase'})
