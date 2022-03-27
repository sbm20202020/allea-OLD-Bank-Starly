from odoo import models, fields


class AccountLoanAgreementReconciliation(models.Model):
    """AccountLoanAgreementReconciliation"""

    _name = 'account.loan.agreement.reconciliation'

    name = fields.Char()
    date = fields.Date('Date of Loan Reconciliation', default=fields.Date.today())
    loan_agreement_id = fields.Many2one('account.loan.agreement', string='Corresponded Loan Agreement')
