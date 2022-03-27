from odoo import fields, models


class AccountMoveLine (models.Model):
    _inherit = 'account.move.line'

    analytic_group_id = fields.Many2one(related='analytic_account_id.group_id', store=True, readonly=True, compute_sudo=True)
