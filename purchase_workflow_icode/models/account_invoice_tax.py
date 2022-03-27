from odoo import models, fields


class AccountInvoiceTax(models.Model):
    """AccountInvoiceTax"""

    _inherit = 'account.move.line'

    state = fields.Selection(related='move_id.state', string='Status', default='draft')
