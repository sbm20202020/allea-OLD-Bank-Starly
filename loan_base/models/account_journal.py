from datetime import datetime
from odoo import models, fields, _
from odoo.tools.misc import formatLang


class AccountJournal(models.Model):
    """Account Journal"""

    _inherit = 'account.journal'

    type = fields.Selection(selection_add=[('journal_payable', 'Journal Payable'),
                                           ('journal_receivable', 'Journal Receivable')])

    def open_action(self):
        """copy of origin function except some tagged override"""
        action_name = self._context.get('action_name', False)
        if not action_name:
            if self.type == 'bank':
                action_name = 'action_bank_statement_tree'
            elif self.type == 'cash':
                action_name = 'action_view_bank_statement_tree'
            elif self.type == 'sale':
                action_name = 'action_invoice_tree1'
            elif self.type == 'purchase':
                action_name = 'action_invoice_tree2'
            else:
                action_name = 'action_move_journal_line'

        _journal_invoice_type_map = {
            ('sale', None): 'out_invoice',
            ('purchase', None): 'in_invoice',
            ('sale', 'refund'): 'out_refund',
            ('purchase', 'refund'): 'in_refund',
            ('bank', None): 'bank',
            ('cash', None): 'cash',
            ('general', None): 'general',
            ('journal_payable', None): 'general',
            ('journal_receivable', None): 'general',
        }
        invoice_type = _journal_invoice_type_map[(self.type, self._context.get('invoice_type'))]

        ctx = self._context.copy()
        ctx.pop('group_by', None)
        ctx.update({
            'journal_type': self.type,
            'default_journal_id': self.id,
            'default_type': invoice_type,
            'type': invoice_type
        })

        [action] = self.env.ref('account.%s' % action_name).read()
        if not self.env.context.get('use_domain'):
            ctx['search_default_journal_id'] = self.id
        action['context'] = ctx
        action['domain'] = self._context.get('use_domain', [])
        account_invoice_filter = self.env.ref('account.view_account_invoice_filter', False)
        if action_name in ['action_invoice_tree1', 'action_invoice_tree2']:
            action['search_view_id'] = account_invoice_filter and account_invoice_filter.id or False
        if action_name in ['action_bank_statement_tree', 'action_view_bank_statement_tree']:
            action['views'] = False
            action['view_id'] = False
        return action

    def get_journal_dashboard_datas(self):
        currency = self.currency_id or self.company_id.currency_id
        number_to_reconcile = last_balance = account_sum = 0
        title = ''
        number_draft = number_waiting = number_late = 0
        sum_draft = sum_waiting = sum_late = 0.0
        if self.type in ['bank', 'cash', 'journal_payable', 'journal_receivable']:
            last_bank_stmt = self.env['account.bank.statement'].search([('journal_id', 'in', self.ids)],
                                                                       order="date desc, id desc", limit=1)
            last_balance = last_bank_stmt and last_bank_stmt[0].balance_end or 0
            # Get the number of items to reconcile for that bank journal
            self.env.cr.execute("""SELECT COUNT(DISTINCT(line.id))
                            FROM account_bank_statement_line AS line
                            LEFT JOIN account_bank_statement AS st
                            ON line.statement_id = st.id
                            WHERE st.journal_id IN %s AND st.state = 'open' AND line.amount != 0.0
                            AND not exists (select 1 from account_move_line aml where aml.statement_line_id = line.id)
                        """, (tuple(self.ids),))
            number_to_reconcile = self.env.cr.fetchone()[0]
            # optimization to read sum of balance from account_move_line
            account_ids = tuple(
                ac for ac in [self.default_debit_account_id.id, self.default_credit_account_id.id] if ac)
            if account_ids:
                amount_field = 'balance' if (
                        not self.currency_id or self.currency_id == self.company_id.currency_id) else 'amount_currency'
                query = """SELECT sum(%s) FROM account_move_line WHERE account_id in %%s AND date <= %%s;""" % (
                    amount_field,)
                self.env.cr.execute(query, (account_ids, fields.Date.today(),))
                query_results = self.env.cr.dictfetchall()
                if query_results and query_results[0].get('sum') is not None:
                    account_sum = query_results[0].get('sum')
        # TODO need to check if all invoices are in the same currency than the journal!!!!
        elif self.type in ['sale', 'purchase']:
            title = _('Bills to pay') if self.type == 'purchase' else _('Invoices owed to you')

            (query, query_args) = self._get_open_bills_to_pay_query()
            self.env.cr.execute(query, query_args)
            query_results_to_pay = self.env.cr.dictfetchall()

            (query, query_args) = self._get_draft_bills_query()
            self.env.cr.execute(query, query_args)
            query_results_drafts = self.env.cr.dictfetchall()

            today = datetime.today()
            query = """SELECT 
                           amount_total, 
                           currency_id AS currency, 
                           type 
                       FROM 
                            account_move 
                       WHERE 
                            journal_id = %s AND 
                            date < %s AND 
                            state = 'open'; """
            self.env.cr.execute(query, (self.id, today))
            late_query_results = self.env.cr.dictfetchall()
            (number_waiting, sum_waiting) = self._count_results_and_sum_amounts(query_results_to_pay, currency)
            (number_draft, sum_draft) = self._count_results_and_sum_amounts(query_results_drafts, currency)
            (number_late, sum_late) = self._count_results_and_sum_amounts(late_query_results, currency)

        difference = currency.round(last_balance - account_sum) + 0.0
        result = {
            'number_to_reconcile': number_to_reconcile,
            'account_balance': formatLang(self.env, currency.round(account_sum) + 0.0, currency_obj=currency),
            'last_balance': formatLang(self.env, currency.round(last_balance) + 0.0, currency_obj=currency),
            'difference': formatLang(self.env, difference, currency_obj=currency) if difference else False,
            'number_draft': number_draft,
            'number_waiting': number_waiting,
            'number_late': number_late,
            'sum_draft': formatLang(self.env, currency.round(sum_draft) + 0.0, currency_obj=currency),
            'sum_waiting': formatLang(self.env, currency.round(sum_waiting) + 0.0, currency_obj=currency),
            'sum_late': formatLang(self.env, currency.round(sum_late) + 0.0, currency_obj=currency),
            'currency_id': currency.id,
            'bank_statements_source': self.bank_statements_source,
            'title': title,
        }
        return result
