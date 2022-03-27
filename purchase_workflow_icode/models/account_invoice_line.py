from odoo import models, fields


class AccountInvoiceLine(models.Model):
    """AccountInvoiceLine"""

    _inherit = 'account.move.line'  # the model name

    state = fields.Selection(related='move_id.state', string='Status', default='draft')
