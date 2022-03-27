# -*- coding: utf-8 -*-

import time

from odoo import fields, models, _, api
from odoo.exceptions import UserError


class AccountReportGeneralLedger(models.TransientModel):
    _inherit = "account.report"
    _description = "General Ledger Report"

    account_ids = fields.Many2many('account.account', string='Accounts', required=False, domain=lambda self: [('company_id', '=', self.env.user.company_id.id)])
    company_ids = fields.Many2many('res.company', string='Companies', required=False, domain=lambda self: [('id', 'in', self.env.user.company_ids.ids)])

    separate_pages_for_accounts_by_print = fields.Boolean(default=False)

    def _print_report(self, data):
        """
            Базовая функция лежит в
            addons/account/wizard/account_report_general_ledger.py


            """
        #data['form'].update({'account_ids':self.read(['account_ids'])[0].get('account_ids', [])})
        data['form'] = self.read(['date_from', 'date_to', 'journal_ids', 'target_move', 'account_ids', 'company_ids'])[0]

        data = self.pre_print_report(data)

        data['form'].update(self.read(['initial_balance', 'sortby'])[0])
        if data['form'].get('initial_balance') and not data['form'].get('date_from'):
            raise UserError(_("You must define a Start Date"))
        records = self.env[data['model']].browse(data.get('ids', []))
        return self.env.ref('account.action_report_general_ledger').with_context(landscape=True,
                                                                                 separate_pages_for_accounts_by_print=self.separate_pages_for_accounts_by_print).report_action(records, data=data)

class ReportGeneralLedger(models.AbstractModel):
    _inherit = 'report.account.report_generalledger'


    @api.model
    def get_report_values(self, docids, data=None):
        """
        Базовая функция лежит в addons/account/report/account_general_ledger.py
        взята сюда полностью, чтобы было на виду, что мы делаем, а не гадать, что за магия.

        можно, для красоты, в целом при рефакторе, можно вызвать супером в переменную и

        ---
        if data['form']['account_ids']:
            accounts = docs if self.model == 'account.account' else self.env['account.account'].search([('id', 'in', data['form']['account_ids'])])
        else:
            accounts = docs if self.model == 'account.account' else self.env['account.account'].search([])

        accounts_res = self.with_context(data['form'].get('used_context',{}))._get_account_move_entry(accounts, init_balance, sortby, display_account)

        super_result.update({'Accounts': accounts_res})

        return super_result
        ---
        но магии не хочется

        """
        if not data.get('form') or not self.env.context.get('active_model'):
            raise UserError(_("Form content is missing, this report cannot be printed."))

        self.model = self.env.context.get('active_model')
        docs = self.env[self.model].browse(self.env.context.get('active_ids', []))

        init_balance = data['form'].get('initial_balance', True)
        sortby = data['form'].get('sortby', 'sort_date')
        display_account = data['form']['display_account']
        codes = []
        if data['form'].get('journal_ids', False):
            codes = [journal.code for journal in self.env['account.journal'].search([('id', 'in', data['form']['journal_ids'])])]

        domain = []
        if data['form']['account_ids']:
            domain.append(('id', 'in', data['form']['account_ids']))

        if data['form']['company_ids']:
            domain.append(('company_id.id', 'in', data['form']['company_ids']))
            data['form']['companies'] = self.env['res.company'].browse(data['form']['company_ids'])
        else:
            data['form']['companies'] = self.env.user.company_ids

        accounts = docs if self.model == 'account.account' else self.env['account.account'].search(domain)


        accounts_res = self.with_context(data['form'].get('used_context',{}))._get_account_move_entry(accounts, init_balance, sortby, display_account)
        return {
            'doc_ids': docids,
            'doc_model': self.model,
            'data': data['form'],
            'docs': docs,
            'time': time,
            'Accounts': accounts_res,
            'print_journal': codes,
            'separate_pages_for_accounts_by_print': self._context.get('separate_pages_for_accounts_by_print'),
        }
