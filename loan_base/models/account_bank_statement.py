from odoo import models, fields


class AccountBankStatement(models.Model):
    """Account Bank Statement"""

    _inherit = 'account.bank.statement'

    loan_agreement_id = fields.Many2one('account.loan.agreement', string="Loan")
