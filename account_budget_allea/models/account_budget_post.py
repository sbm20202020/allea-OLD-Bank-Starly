from odoo import models, fields


class AccountBudgetPost(models.Model):
    """Account Budget Post"""

    _inherit = 'account.budget.post'

    def _default_employee(self):
        return self.env['hr.employee'].search([('user_id', '=', self._uid)], limit=1)

    company_id = fields.Many2one('res.company', 'Company', required=False)
    employee_id = fields.Many2one('hr.employee', 'Responsible', default=_default_employee)
    account_ids = fields.Many2many('account.account', 'account_budget_rel', 'budget_id', 'account_id', 'Accounts',
                                   domain="[('deprecated', '=', False)]")
