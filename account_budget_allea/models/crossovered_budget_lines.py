from odoo import models, fields, api


class CrossoveredBudgetLines(models.Model):
    _inherit = 'crossovered.budget.lines'

    practical_amount = fields.Monetary(
        compute='_compute_practical_amount', string='Practical Amount', help="Amount really earned/spent.", store=True)
    account_ids = fields.Many2many(related='general_budget_id.account_ids', string="Accounts")

    @api.depends('analytic_account_id.line_ids', 'account_ids')
    def _compute_practical_amount(self):
        super()._compute_practical_amount()
