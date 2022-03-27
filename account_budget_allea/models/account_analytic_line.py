from odoo import models, fields


class AccountAnalyticLine(models.Model):
    """AccountAnalyticLine"""

    _inherit = "account.analytic.line"

    company_id = fields.Many2one(related='move_id.company_id', string='Company', required=True)
