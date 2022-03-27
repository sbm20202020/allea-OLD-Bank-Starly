from odoo import models, fields, api


class CrossoveredBudgetLines(models.Model):

    _inherit = 'crossovered.budget.lines'

    practical_amount = fields.Float(compute='compute_practical_amount', string='Practical Amount', digits=0,
                                    store=True)
    account_ids = fields.Many2many(related='general_budget_id.account_ids', string="Accounts")
    analytic_line_ids = fields.Many2many('account.analytic.line', compute='compute_analytic_lines',
                                         string='Analytic lines', store=True)

    @api.depends('analytic_account_id.line_ids', 'account_ids')
    def compute_analytic_lines(self):
        for budget_line in self:
            acc_ids = budget_line.account_ids.ids
            date_to = self.env.context.get('wizard_date_to') or budget_line.date_to
            date_from = self.env.context.get('wizard_date_from') or budget_line.date_from
            an_id = budget_line.analytic_account_id.id
            if an_id:
                self.env.cr.execute("""
                                SELECT id
                                FROM account_analytic_line
                                WHERE account_id=%s
                                    AND (date between to_date(%s,'yyyy-mm-dd') AND to_date(%s,'yyyy-mm-dd'))
                                    AND general_account_id=ANY(%s)""",
                                    (an_id, date_from, date_to, acc_ids,))
                result = [x[0] for x in self.env.cr.fetchall()]
            budget_line.analytic_line_ids = result

    @api.depends('analytic_account_id.line_ids', 'account_ids')
    def compute_practical_amount(self):
        super()._compute_practical_amount()
