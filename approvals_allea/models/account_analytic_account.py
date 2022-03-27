from odoo import models, fields


class AccountAnalyticAccount(models.Model):
    """Account analytic account"""
    _inherit = 'account.analytic.account'

    user_ids = fields.Many2many('res.users', string='Allowed Users')
