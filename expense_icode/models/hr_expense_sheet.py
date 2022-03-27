"""
Module is designed taking into account the odoo guidelines:
  `https://www.odoo.com/documentation/12.0/reference/guidelines.html`
"""
# === Standard library imports ===
import logging

# === Init logger ================
_logger = logging.getLogger(__name__)

# === Third party imports ========
# import pandas

# === Imports of odoo ============
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

# === Imports from odoo addons ===
# from odoo.addons.website.models.website import slug

# === Local application imports ==
# from ..exceptions import BaseModuleNameError


# === CONSTANTS ==================
# SPEED_OF_LIGHT_M_S = 299792458

# === Module init variables ======
# myvar = 'test'


class HrExpenseSheet(models.Model):
    """HrExpenseSheet"""
    # - In a Model attribute order should be
    # === Private attributes (``_name``, ``_description``, ``_inherit``, ...)
    _inherit = 'hr.expense.sheet'  # the model name

    accounting_date = fields.Date(string="Date", default=fields.Date.context_today)

    # === Default method and ``_default_get``
    @api.model
    def default_get(self, fields):
        result = super().default_get(fields)
        context = self.env.context
        bank_journal_id = context.get('default_bank_journal_id')
        if bank_journal_id:
            result.update({'bank_journal_id': bank_journal_id})
        return result

    def _get_journal_domain(self):
        domain = [('company_id', '=', self.company_id.id), ('type', 'in', ['cash', 'bank'])]
        return domain

    # === Field declarations
    # analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags')
    # === Compute, inverse and search methods in the same order as field declaration
    # === Selection method (methods used to return computed values for selection fields)

    # === Constrains methods (``@api.constrains``) and onchange methods (``@api.onchange``)

    @api.constrains('accounting_date')
    def _constraint_accounting_date(self):
        if self.account_move_id.date != self.accounting_date:
            self.account_move_id.write({'date': self.accounting_date})

    @api.onchange('company_id')
    def _onchange_company_id(self):
        AccountJournal = self.env['account.journal']
        if self.payment_mode == 'company_account' and self.bank_journal_id.company_id.id != self.company_id.id:
            self.bank_journal_id = AccountJournal.search(self._get_journal_domain(), limit=1)

    @api.onchange('expense_line_ids')
    def _onchange_expense_line_ids(self):
        if len(self.expense_line_ids) == 1:
            self.company_id = self.expense_line_ids[:1].company_id
            if self.payment_mode == 'company_account':
                self.bank_journal_id = self.expense_line_ids[:1].bank_journal_id
            else:
                self.journal_id = self.expense_line_ids[:1].journal_id

    @api.constrains('expense_line_ids')
    def _constraint_expense_line_ids(self):
        for expense_sheet in (es for es in self if es.payment_mode == 'company_account'):
            for bank_journal_id in (el.bank_journal_id for el in expense_sheet.expense_line_ids):
                if bank_journal_id.id != expense_sheet.bank_journal_id.id:
                    raise ValidationError(_('Expense lines must have the same Bank Journal.'))

    # === CRUD methods (ORM overrides)
    # === Action methods
    # === And finally, other business methods.
