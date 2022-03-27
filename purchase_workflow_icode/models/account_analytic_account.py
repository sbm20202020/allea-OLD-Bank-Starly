from odoo import models, fields


class AccountAnalyticAccount(models.Model):
    """Account Analytic Account"""

    _inherit = "account.analytic.account"

    def _default_currency(self):
        if self.company_id:
            res = self.company_id.currency_id
        else:
            res = self.env.user.company_id.currency_id
        return res

    company_id = fields.Many2one('res.company', string='Company', required=False)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=False, required=True, store=True,
                                  default=_default_currency)
    department_ids = fields.Many2many('hr.department', 'rel_analytic_analytic_account_hr_department',
                                      string='Department')
