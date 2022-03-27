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
from odoo.exceptions import UserError

# === Imports from odoo addons ===
# from odoo.addons.website.models.website import slug
from odoo.addons import decimal_precision as dp

# === Local application imports ==
# from ..exceptions import BaseModuleNameError


# === CONSTANTS ==================
# SPEED_OF_LIGHT_M_S = 299792458

# === Module init variables ======
# myvar = 'test'


class HrExpense(models.Model):
    """HrExpense"""
    # - In a Model attribute order should be
    # === Private attributes (``_name``, ``_description``, ``_inherit``, ...)
    _inherit = 'hr.expense'  # the model name

    # === Default method and ``_default_get``
    @api.model
    def _default_bank_journal(self):
        if self._context.get('default_bank_journal_id', False):
            return self.env['account.journal'].browse(self._context.get('default_bank_journal_id'))
        company_id = self._context.get('company_id', self.env.user.company_id.id)
        domain = [('type', 'in', ['cash', 'bank']), ('company_id', '=', company_id), ]
        return self.env['account.journal'].search(domain, limit=1)

    @api.model
    def _default_journal(self):
        journal_id = self.env['ir.model.data'].xmlid_to_object('hr_expense.hr_expense_account_journal')
        company_id = self._context.get('company_id', self.env.user.company_id.id)
        journal_id = journal_id or self.env['account.journal'].search([('type', '=', 'purchase'),
                                                                       ('company_id', '=', company_id)], limit=1)
        return journal_id

    def _get_journal_domain(self):
        domain = [('company_id', '=', self.company_id.id), ('type', 'in', ['cash', 'bank'])]
        return domain
    # === Field declarations
    tax_amount = fields.Float(string='Tax Sum',
                              # INFO: temporary locked <Pavel 2019-03-07>
                              # readonly=True,
                              # required=True,
                              # states={'draft': [('readonly', False)], 'refused': [('readonly', False)]},
                              digits=dp.get_precision('Product Price'),
                              compute='_compute_tax_amount')
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags')
    bank_account_id = fields.Many2one(related='bank_journal_id.bank_account_id', string='Bank Account', readonly=True)
    bank_id = fields.Many2one(related='bank_journal_id.bank_id', string='Bank', readonly=True)
    bank_journal_id = fields.Many2one('account.journal', string='Bank Journal',
                                 # INFO: temporary locked <Pavel 2019-03-07>
                                 # required=True, readonly=True, states={'draft': [('readonly', False)]},
                                 default=_default_bank_journal,
                                 domain="[('type', 'in', ['cash', 'bank']), ('company_id', '=', company_id)]")

    journal_id = fields.Many2one('account.journal', string='Expense Journal',
                                 default=_default_journal,
                                 help="The journal used when the expense is done.",
                                 domain="[('type', '=', 'purchase'), ('company_id', '=', company_id)]", )

    tax_line_ids = fields.One2many('hr.expense.taxline', 'expense_id', string='Tax Lines',
                                   readonly=True, states={'draft': [('readonly', False)]}, copy=True)

    # === Compute, inverse and search methods in the same order as field declaration
    @api.depends('quantity', 'unit_amount', 'tax_ids', 'currency_id', 'tax_line_ids')
    def _compute_tax_amount(self):
        for expense in self:
            tax_amount = [tax_line.amount for tax_line in expense.tax_line_ids] or [0]
            expense.tax_amount = sum(tax_amount)

    # INFO: this method overrides base model method <Pavel 2019-03-07>
    @api.depends('quantity', 'unit_amount', 'tax_ids', 'currency_id', 'tax_line_ids')
    def _compute_amount(self):
        for expense in self:
            expense.untaxed_amount = expense.unit_amount * expense.quantity
            taxes = expense.tax_ids.compute_all(expense.unit_amount, expense.currency_id, expense.quantity,
                                                expense.product_id, expense.employee_id.user_id.partner_id)
            # patching taxes
            for tax in taxes['taxes']:
                for tax_line in expense.tax_line_ids:
                    tax_line_dict = tax_line.get_dict()
                    if tax['id'] == tax_line_dict['id']:
                        if tax['amount'] != tax_line_dict['amount']:
                            taxes['total_included'] -= tax['amount']
                            taxes['total_included'] += tax_line_dict['amount']

            expense.total_amount = taxes.get('total_included')

    # === Selection method (methods used to return computed values for selection fields)
    # === Constrains methods (``@api.constrains``) and onchange methods (``@api.onchange``)
    @api.onchange('company_id')
    def _onchange_company_id(self):
        AccountJournal = self.env['account.journal']
        self.bank_journal_id = AccountJournal.search(self._get_journal_domain(), limit=1)

    @api.onchange('quantity', 'unit_amount', 'tax_ids', 'currency_id')
    def _onchange_tax_ids(self):
        taxes = self.tax_ids.compute_all(self.unit_amount, self.currency_id, self.quantity,
                                         self.product_id, self.employee_id.user_id.partner_id)
        tax_line_ids = self.tax_line_ids.filtered('manual')
        for tax in taxes['taxes']:
            tax['tax_id'] = tax.pop('id', False)
            tax_line_ids += tax_line_ids.new(tax)
        self.tax_line_ids = tax_line_ids
        # keys = 'base, expense_id, tax_id, manual, name, amount, account_analytic_id, account_id, sequence'.split(', ')
        # taxes_grouped = {}
        # for tax in self.tax_ids:
        #     tax_info = dict(tax_id=tax.id,
        #                     name=tax.name,
        #                     expense_id=self.id,
        #                     amount=tax['amount'],
        #                     base=0.0,
        #                     manual=False,
        #                     sequence=tax['sequence'],
        #                     account_analytic_id=tax['analytic'] and self.analytic_account_id.id or False,
        #                     account_id=False,
        #                     )
        #     taxes_grouped[tax.id] = {key: tax_info.get(key, False) for key in keys}
        #
        # tax_lines = self.tax_line_ids.filtered('manual')
        # for tax in taxes_grouped.values():
        #     tax_lines += tax_lines.new(tax)
        # self.tax_line_ids = tax_lines
        # return

    @api.onchange('payment_mode')
    def _onchange_payment_mode(self):
        if self.payment_mode == 'own_account':
            self.bank_journal_id = False
            self.journal_id = False
        elif self.payment_mode == 'company_account':
            self.journal_id = False

    # === CRUD methods (ORM overrides)
    # === Action methods

    # OVERRIDE
    def submit_expenses(self):
        result = super().submit_expenses()
        payment_mode = set(self.mapped('payment_mode'))
        bank_journal_id = self.mapped('bank_journal_id.id')
        journal_id = self.mapped('journal_id.id')
        analytic_tag_ids = self.mapped('analytic_tag_ids').ids
        if len(payment_mode) > 1:
            raise UserError(_("Cannot create expenses for employee and company in one expense report."))
        elif payment_mode == {'own_account'} and len(journal_id) > 1:
            raise UserError(_("Cannot create expenses for different journals."))
        elif payment_mode == {'company_account'} and len(bank_journal_id) > 1:
            raise UserError(_("Cannot create expenses for different bank journals."))

        vals = dict(default_bank_journal_id=self[:1].bank_journal_id.id,
                    default_journal_id=self[:1].journal_id.id,
                    default_analytic_tag_ids=self[:1].analytic_tag_ids.ids)
        if 'context' in result:
            result['context'].update(vals)

        return result

    # OVERRIDE
    def _move_line_get(self):
        account_move = []
        for expense in self:
            move_line = expense._prepare_move_line_value()
            account_move.append(move_line)

            # Calculate tax lines and adjust base line
            taxes = expense.tax_ids.with_context(round=True).compute_all(expense.unit_amount, expense.currency_id, expense.quantity, expense.product_id)

            # <PATCHING TAXES>
            for tax in taxes['taxes']:
                for tax_line in expense.tax_line_ids:
                    tax_line_dict = tax_line.get_dict()
                    if tax['id'] == tax_line_dict['id']:
                        if tax['amount'] != tax_line_dict['amount']:
                            taxes['total_included'] -= tax['amount']
                            taxes['total_included'] += tax_line_dict['amount']
                            tax['amount'] = tax_line_dict['amount']
            # </PATCHING TAXES>

            account_move[-1]['price'] = taxes['total_excluded']
            account_move[-1]['tax_ids'] = [(6, 0, expense.tax_ids.ids)]
            for tax in taxes['taxes']:
                account_move.append({
                    'type': 'tax',
                    'name': tax['name'],
                    'price_unit': tax['amount'],
                    'quantity': 1,
                    'price': tax['amount'],
                    'account_id': tax['account_id'] or move_line['account_id'],
                    'tax_line_id': tax['id'],
                    'expense_id': expense.id,
                })
        return account_move

    # OVERRIDE
    def _prepare_move_line(self, line):
        '''
        This function prepares move line of account.move related to an expense
        '''
        result = super()._prepare_move_line(line)
        if 'expense_id' in result:
            HrExpense = self.env['hr.expense']
            result['analytic_tag_ids'] = [(6, 0, HrExpense.browse(line['expense_id']).analytic_tag_ids.ids)]
        return result

    # === And finally, other business methods.
