from odoo import models, fields


class AccountLoanAgreementStage(models.Model):
    """Agreement Stage"""

    _name = 'account.loan.agreement.stage'
    _order = 'sequence, id'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer('Sequence', default=10)
    is_close = fields.Boolean(string='Closing Kanban Stage')
    fold = fields.Boolean('Folded', help='Folded in kanban view')
    on_change = fields.Boolean(string='Change Probability Automatically')
