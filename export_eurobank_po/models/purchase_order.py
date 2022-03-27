from odoo import models, fields


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    vendor_bank_account_id = fields.Many2one('res.partner.bank', string='Vendor Bank Account', required=True)
    company_bank_account_id = fields.Many2one('account.journal', string='Company Bank Account')
