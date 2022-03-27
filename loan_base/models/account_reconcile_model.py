from odoo import models, fields, api


class AccountReconcileModel(models.Model):
    """Reconcile Model"""

    _inherit = 'account.reconcile.model'  # the model name

    amount_type = fields.Selection(selection_add=[('interest_first_principal_second', 'Interest first'),
                                                  ('principal_first_interest_second', 'Interest second'), ])
    second_amount_type = fields.Selection(selection_add=[('interest_first_principal_second', 'Principal second'),
                                                         ('principal_first_interest_second', 'Principal first'), ])
    match_loan = fields.Boolean(string='Loan Is Set',
                                help='The reconciliation model will only be applied when a loan is set.')
    match_loan_id = fields.Many2one('account.loan.agreement', string='Restrict Loan to',
                                    help='The reconciliation model will only be applied to the selected loan.')

    def _apply_conditions(self, query, params):
        self.ensure_one()
        rule = self
        query, params = super()._apply_conditions(query=query, params=params)
        # Filter on loans.
        if rule.match_loan:
            query += ' AND st_line.loan_agreement_id != 0'
            if rule.match_loan_id:
                query += ' AND st_line.loan_agreement_id IN %s'
                params += [tuple((rule.match_loan_id.id,))]
        return query, params

    def _get_write_off_move_lines_dict(self, st_line, move_lines=None):
        self.ensure_one()
        new_aml_dicts = super()._get_write_off_move_lines_dict(st_line=st_line, move_lines=move_lines)
        if (self.match_loan
                and st_line.loan_agreement_id.id
                and len(new_aml_dicts) == 2
                and self.amount_type == 'interest_first_principal_second'):
            balance = st_line.get_balance_by_move_lines(move_lines=move_lines)
            balance = abs(balance)  # TODO: fix this temporary solution <Pavel 2019-04-25>
            agreement_id = st_line.loan_agreement_id
            line1_balance, line2_balance = agreement_id.get_interest_principal_on_date_by_balance(
                dt=st_line.date,
                balance=balance,
                amount_type=self.amount_type)
            new_values_line1 = {
                'debit': 0,
                'credit': line1_balance,
                'loan_agreement_id': agreement_id.id,
            }
            new_values_line2 = {
                'debit': 0,
                'credit': line2_balance,
                'loan_agreement_id': agreement_id.id,
            }
            new_aml_dicts[0].update(new_values_line1)
            new_aml_dicts[1].update(new_values_line2)
            self.write(dict(amount=line1_balance, second_amount=line2_balance, ))
        return new_aml_dicts

    @api.model
    def create_rule_for_loan(self, agreement_id=None):
        if agreement_id is not None:
            values = {
                'name': 'Reconciliation Model for Loans',
                'label': 'interest repay',
                'second_label': 'principal repay',
                'rule_type': 'writeoff_suggestion',
                'match_nature': 'amount_received',
                'match_loan': True,
                'amount_type': 'interest_first_principal_second',
                'second_amount_type': 'interest_first_principal_second',
                'amount': 0,
                'second_amount': 0,
                'has_second_line': True,
            }
            rule = self.search([('name', '=ilike', values['name'])], limit=1) or self.create([values])
            return rule
