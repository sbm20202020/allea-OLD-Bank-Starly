# -*- coding: utf-8 -*-
from odoo import api, models, fields


class AccountBankStatementLine(models.Model):
    _name = 'account.move.statement.line'
    _inherit = 'account.bank.statement.line'

class AccountMoveStatement(models.Model):
    _name = 'account.move.statement'
    _inherit = "account.bank.statement"
    _description = "Moves Statement"
    # balance_end_real_is_dirty = fields.Boolean(default=False)

    @api.model
    def create(self, vals):
        if vals.get('name'):
            journal = self.env['account.journal'].browse(
                vals.get('journal_id'))
            if journal.enforce_sequence:
                vals['name'] = '/'
        return super(AccountMoveStatement, self).create(vals)

    @api.onchange('balance_end_real')
    def balance_end_real_changed(self):
        self.balance_end_real_is_dirty = True

    @api.depends('line_ids', 'balance_start', 'line_ids.amount', 'balance_end_real')
    def _end_balance(self):
        super()._end_balance()
        if not self.balance_end_real_is_dirty:
            self.balance_end_real = self.balance_end
            self.balance_end_real_is_dirty = False
