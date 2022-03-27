from odoo import models, fields


class AccountLoanAgreementRepaymentLine(models.Model):
    """Repayment Line"""

    _name = 'account.loan.agreement.repayment.line'

    loan_agreement_id = fields.Many2one('account.loan.agreement')
    date = fields.Date('Date')
    principal = fields.Float('Principal')
    interest = fields.Float('Interest')
    total_payment = fields.Float('Total Payment')
