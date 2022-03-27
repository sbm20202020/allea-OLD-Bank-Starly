from odoo import models, fields, api


class AccountMove(models.Model):
    """AccountMove"""

    _inherit = 'account.move'

    loan_agreement_id = fields.Many2one('account.loan.agreement', string='Corresponding Loan Agreement')

    @api.constrains('line_ids')
    def _constrain_line_ids(self):
        loan_agreement = self.env['account.loan.agreement']
        for move in self:
            for move_line in move.line_ids:
                move_line.constrains_loan_agreement_id()
            agreement_ids = loan_agreement.search([])
            for agreement_id in agreement_ids:
                agreement_id._compute_principal_outstanding()
                agreement_id._compute_interest_outstanding()
                agreement_id._compute_total_outstanding()
