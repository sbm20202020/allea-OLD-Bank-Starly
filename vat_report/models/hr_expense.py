"""
Module is designed taking into account the odoo guidelines:
  `https://www.odoo.com/documentation/12.0/reference/guidelines.html`
"""
# === Standard library imports ===
import logging

# === Init logger ================
from contextlib import suppress

_logger = logging.getLogger(__name__)

# === Third party imports ========
# import pandas

# === Imports of odoo ============
from odoo import models, fields, api, _, tools  # noqa: F401 #pylint: disable=W0611


# === Imports from odoo addons ===
# from odoo.addons.website.models.website import slug

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
    _description = __doc__  # the model's informal name
    # === Default method and ``_default_get``

    # === Field declarations
    # MIMICRY FIELDS
    exchange_rate = fields.Float('Exchange Rate', compute='_compute_exchange_rate')
    amount_tax_euro = fields.Monetary(string='Total', readonly=True, compute='_compute_euro_amounts')
    amount_untaxed_euro = fields.Monetary(string='Total', readonly=True, compute='_compute_euro_amounts')
    amount_total_euro = fields.Monetary(string='Total', readonly=True, compute='_compute_euro_amounts')
    amount_total_non_eu = fields.Monetary(string='Total', readonly=True, compute='_compute_eu_non_eu_amounts')
    amount_total_eu = fields.Monetary(string='Total', readonly=True, compute='_compute_eu_non_eu_amounts')
    amount_total_non_eu_euro = fields.Monetary(string='Total', readonly=True, compute='_compute_eu_non_eu_amounts')
    amount_total_eu_euro = fields.Monetary(string='Total', readonly=True, compute='_compute_eu_non_eu_amounts')
    # amount_tax_non_eu = fields.Monetary(string='Total', readonly=True, compute='_compute_eu_non_eu_amounts')
    # amount_tax_eu = fields.Monetary(string='Total', readonly=True, compute='_compute_eu_non_eu_amounts')

    disbursements_amount = fields.Monetary(compute='_compute_disbursements_vat_net_amounts')
    vat_amount = fields.Monetary(compute='_compute_disbursements_vat_net_amounts')
    net_amount = fields.Monetary(compute='_compute_disbursements_vat_net_amounts')
    disbursements_amount_euro = fields.Monetary(compute='_compute_disbursements_vat_net_amounts_euro')
    vat_amount_euro = fields.Monetary(compute='_compute_disbursements_vat_net_amounts_euro')
    net_amount_euro = fields.Monetary(compute='_compute_disbursements_vat_net_amounts_euro')

    article_11b = fields.Char(string='Article 11b', compute='_compute_article_11b')

    narration = fields.Text(related='description')
    invoice_date = fields.Date(related='date')
    number_of_invoice = fields.Char(related='name')

    amount_total_company_signed = fields.Monetary(compute='_compute_amount_total_company_signed')
    amount_tax = fields.Float(compute='_compute_amount_tax')
    amount_untaxed = fields.Float(related='untaxed_amount')
    # amount_total = fields.Float(related='total_amount')
    partner_id_name = fields.Char(related='employee_id.name')
    credit_sign = fields.Float(compute='_compute_credit_sign')

    # === Compute, inverse and search methods in the same order as field declaration
    def _compute_exchange_rate(self):
        for invoice_id in self:
            # invoice_id.exchange_rate = invoice_id.amount_total_signed / invoice_id.amount_total_company_signed
            exchange_rate = 1
            with suppress(ZeroDivisionError):
                exchange_rate = abs(invoice_id.total_amount / invoice_id.amount_total_euro)
                invoice_id.exchange_rate = tools.float_round(exchange_rate, precision_digits=4)

    def _compute_euro_amounts(self):
        currency_euro = self.env.ref('base.EUR')
        for expense_id in self:
            expense_currency_id = expense_id.currency_id.with_context(date=expense_id.invoice_date)
            expense_id.amount_tax_euro = expense_currency_id.compute(expense_id.amount_tax, currency_euro)
            expense_id.amount_untaxed_euro = expense_currency_id.compute(expense_id.amount_untaxed, currency_euro)
            expense_id.amount_total_euro = expense_currency_id.compute(expense_id.total_amount, currency_euro)

    @api.depends('company_id.partner_id.is_in_eu')
    def _compute_eu_non_eu_amounts(self):
        for expense_id in self:
            if expense_id.company_id.partner_id.is_in_eu:
                expense_id.amount_total_eu = expense_id.total_amount
                expense_id.amount_total_non_eu = 0
                expense_id.amount_total_eu_euro = expense_id.amount_total_euro
                expense_id.amount_total_non_eu_euro = 0
                # invoice_id.amount_tax_eu = invoice_id.amount_tax_euro
                # invoice_id.amount_tax_non_eu = 0

            else:
                expense_id.amount_total_eu = 0
                expense_id.amount_total_non_eu = expense_id.total_amount
                expense_id.amount_total_eu_euro = 0
                expense_id.amount_total_non_eu_euro = expense_id.amount_total_euro
                # invoice_id.amount_tax_eu = 0
                # invoice_id.amount_tax_non_eu = invoice_id.amount_tax_euro

    def _compute_disbursements_vat_net_amounts(self):
        for expense_id in self:
            if expense_id.amount_tax:
                expense_id.disbursements_amount = 0
                expense_id.vat_amount = expense_id.amount_tax
                expense_id.net_amount = expense_id.amount_untaxed
            else:
                expense_id.disbursements_amount = expense_id.total_amount
                expense_id.vat_amount = 0
                expense_id.net_amount = 0
                expense_id.amount_total_eu = expense_id.total_amount

    def _compute_disbursements_vat_net_amounts_euro(self):
        currency_euro = self.env.ref('base.EUR')
        for expense_id in self:
            expense_currency_id = expense_id.currency_id.with_context(date=expense_id.invoice_date)
            expense_id.disbursements_amount_euro = expense_currency_id.compute(expense_id.disbursements_amount, currency_euro)
            expense_id.vat_amount_euro = expense_currency_id.compute(expense_id.vat_amount, currency_euro)
            expense_id.net_amount_euro = expense_currency_id.compute(expense_id.net_amount, currency_euro)

    def _compute_article_11b(self):
        for expense_id in self:
            for analytic_tag_id_name in expense_id.analytic_tag_ids.mapped('name'):
                if analytic_tag_id_name == 'Article 11b':
                    expense_id.article_11b = '11b'
                    break
            else:
                expense_id.article_11b = ''

    def _compute_amount_total_company_signed(self):
        for expense_id in self:
            amount_total_company_signed = expense_id.total_amount
            company_currency_id = expense_id.company_id.currency_id
            expense_currency_id = expense_id.currency_id
            if expense_currency_id and expense_currency_id != company_currency_id:
                expense_currency_id_with_context = expense_id.currency_id.with_context(date=expense_id.invoice_date)
                amount_total_company_signed = expense_currency_id_with_context.compute(amount_total_company_signed,
                                                                                       company_currency_id)

            # sign = -1 if expense_id.invoice_id.type in ['in_refund', 'out_refund'] else 1
            sign = 1
            expense_id.amount_total_company_signed = sign * amount_total_company_signed

    def _compute_amount_tax(self):
        for expense_id in self:
            expense_id.amount_tax = expense_id.total_amount - expense_id.amount_untaxed

    def _compute_credit_sign(self):
        for rec_id in self:
            rec_id.credit_sign = 1

    # === Selection method (methods used to return computed values for selection fields)
    # === Constrains methods (``@api.constrains``) and onchange methods (``@api.onchange``)
    # === CRUD methods (ORM overrides)
    # === Action methods
    # === And finally, other business methods.
    def get_class_of_invoice(self):
        self.ensure_one()
        expense_id = self
        AccountInvoice = self.env['account.move']
        class_dict = AccountInvoice.get_class_dict()
        result = 'default_class'
        tag_ids_filtered = expense_id.analytic_tag_ids.filtered(lambda tag_id: tag_id in class_dict)
        if tag_ids_filtered:
            result = class_dict[tag_ids_filtered[:1]]
        return result

    # for backward compatibility
    get_class_of_expense = get_class_of_invoice
