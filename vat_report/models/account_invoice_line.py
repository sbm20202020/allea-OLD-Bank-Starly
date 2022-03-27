# === Init logger ================
from contextlib import suppress
# === Third party imports ========
# import pandas

# === Imports of odoo ============
from odoo import models, fields, api, _, tools  # noqa: F401 #pylint: disable=W0611
from odoo.exceptions import ValidationError


class AccountInvoiceLine(models.Model):
    """AccountInvoiceLine"""
    # - In a Model attribute order should be
    # === Private attributes (``_name``, ``_description``, ``_inherit``, ...)
    _inherit = 'account.move.line'  # the model name
    # === Default method and ``_default_get``
    # === Field declarations
    # MIMICRY FIELDS
    exchange_rate = fields.Float('Exchange Rate', compute='_compute_exchange_rate')

    amount_total_non_eu = fields.Monetary(string='Total', readonly=True, compute='_compute_eu_non_eu_amounts')
    amount_total_non_eu_euro = fields.Monetary(string='Total', readonly=True, compute='_compute_eu_non_eu_amounts')
    amount_total_eu = fields.Monetary(string='Total', readonly=True, compute='_compute_eu_non_eu_amounts')
    amount_total_eu_euro = fields.Monetary(string='Total', readonly=True, compute='_compute_eu_non_eu_amounts')

    disbursements_amount = fields.Monetary(compute='_compute_disbursements_vat_net_amounts')
    disbursements_amount_euro = fields.Monetary(compute='_compute_disbursements_vat_net_amounts_euro')

    article_11b = fields.Char(string='Article 11b', compute='_compute_article_11b')

    number_of_invoice = fields.Char(related='move_id.number_of_invoice')

    amount_total_company_signed = fields.Monetary(compute='_compute_amount_total_company_signed')
    amount_tax = fields.Monetary(compute='_compute_amount_tax')
    amount_untaxed = fields.Monetary(related='tax_base_amount')
    amount_total = fields.Monetary(compute='_compute_amount_total')
    amount_tax_curr = fields.Monetary(string='Total', readonly=True, compute='_compute_euro_amounts')
    amount_untaxed_curr = fields.Monetary(string='Total', readonly=True, compute='_compute_euro_amounts')
    amount_total_curr = fields.Monetary(string='Total', readonly=True, compute='_compute_euro_amounts')
    credit_sign = fields.Float(compute='_compute_credit_sign')

    # === Compute, inverse and search methods in the same order as field declaration
    def _compute_exchange_rate(self):
        for aml_id in self:
            if aml_id.amount_currency:
                exchange_rate = aml_id.amount_currency / aml_id.amount_residual
            else:
                exchange_rate = 1.0
            aml_id.exchange_rate = tools.float_round(exchange_rate, precision_digits=4)

    def _compute_euro_amounts(self):
        for invoice_line_id in self:
            invoice_currency_id = invoice_line_id.currency_id
            company_currency_id = invoice_line_id.company_id.currency_id
            invoice_line_id.amount_tax_curr = company_currency_id._convert(invoice_line_id.amount_tax, invoice_currency_id, invoice_line_id.company_id, invoice_line_id.date)
            invoice_line_id.amount_untaxed_curr = company_currency_id._convert(invoice_line_id.tax_base_amount, invoice_currency_id, invoice_line_id.company_id, invoice_line_id.date)
            invoice_line_id.amount_total_curr = invoice_line_id.amount_tax_curr + invoice_line_id.amount_untaxed_curr

    @api.depends('partner_id.is_in_eu')
    def _compute_eu_non_eu_amounts(self):
        for invoice_line_id in self:
            if invoice_line_id.partner_id.is_in_eu:
                invoice_line_id.amount_total_eu = invoice_line_id.amount_untaxed
                invoice_line_id.amount_total_eu_euro = invoice_line_id.amount_untaxed_curr
                invoice_line_id.amount_total_non_eu = 0
                invoice_line_id.amount_total_non_eu_euro = 0
            else:
                invoice_line_id.amount_total_eu = 0
                invoice_line_id.amount_total_eu_euro = 0
                invoice_line_id.amount_total_non_eu = invoice_line_id.amount_untaxed
                invoice_line_id.amount_total_non_eu_euro = invoice_line_id.amount_untaxed_curr

    def _compute_disbursements_vat_net_amounts(self):
        for invoice_line_id in self:
            if invoice_line_id.tax_base_amount:
                invoice_line_id.disbursements_amount = 0
            else:
                invoice_line_id.disbursements_amount = invoice_line_id.amount_residual

    def _compute_disbursements_vat_net_amounts_euro(self):
        for invoice_line_id in self:
            invoice_currency_id = invoice_line_id.currency_id.with_context(date=invoice_line_id.date)
            company_currency_id = invoice_line_id.company_id.currency_id
            invoice_line_id.disbursements_amount_euro = company_currency_id._convert(invoice_line_id.disbursements_amount, invoice_currency_id, invoice_line_id.company_id, invoice_line_id.date)

    def _compute_article_11b(self):
        for invoice_line_id in self:
            for analytic_tag_id_name in invoice_line_id.analytic_tag_ids.mapped('name'):
                if analytic_tag_id_name == 'Article 11b':
                    invoice_line_id.article_11b = '11b'
                    break
            else:
                invoice_line_id.article_11b = ''

    def _compute_amount_total_company_signed(self):
        for invoice_line_id in self:
            amount_total_company_signed = invoice_line_id.price_total
            company_currency_id = invoice_line_id.company_currency_id
            invoice_currency_id = invoice_line_id.currency_id
            company_id = invoice_line_id.company_id
            date = invoice_line_id.date
            if invoice_currency_id and invoice_currency_id != company_currency_id:
                amount_total_company_signed = invoice_currency_id._convert(amount_total_company_signed, company_currency_id, company_id, date)
            sign = -1 if invoice_line_id.move_id.type in ['in_refund', 'out_refund'] else 1
            invoice_line_id.amount_total_company_signed = sign * amount_total_company_signed

    def _compute_amount_tax(self):
        for invoice_line_id in self:
            if invoice_line_id.tax_base_amount:
                invoice_line_id.amount_tax = invoice_line_id.amount_total_company_signed
            else:
                invoice_line_id.amount_tax = 0

    def _compute_amount_total(self):
        for invoice_line_id in self:
            invoice_line_id.amount_total = invoice_line_id.amount_tax + invoice_line_id.amount_untaxed

    def _compute_credit_sign(self):
        credit_note_types = ('out_refund',  # Customer Credit Note
                             'in_refund',  # Vendor Credit Note
                             )
        for invoice_line_id in self:
            invoice_id = invoice_line_id.invoice_id
            if invoice_id.type in credit_note_types:
                invoice_line_id.credit_sign = -1
            else:
                invoice_line_id.credit_sign = 1

    # === Selection method (methods used to return computed values for selection fields)

    # === Constrains methods (``@api.constrains``) and onchange methods (``@api.onchange``)
    @api.constrains('analytic_tag_ids')
    def constrains_analytic_tag_ids(self):
        AccountInvoice = self.env['account.move']
        class_dict = AccountInvoice.get_class_dict()
        for invoice_line_id in self:
            invoice_id = invoice_line_id.invoice_id
            analytic_tag_ids = invoice_line_id.analytic_tag_ids
            matched_analytic_tag_ids = [tag_id for tag_id in analytic_tag_ids if tag_id in class_dict]
            if len(matched_analytic_tag_ids) > 1:
                raise ValidationError(
                    _('For invoice line in invoice `{}` must be only one VAT analytic tag!').format(invoice_id.name))

    # === CRUD methods (ORM overrides)
    # === Action methods
    # === And finally, other business methods.

    def get_class_of_invoice_line(self):
        self.ensure_one()
        invoice_line_id = self
        AccountInvoice = self.env['account.move']
        class_dict = AccountInvoice.get_class_dict()
        result = 'default_class'
        analytic_tag_ids = invoice_line_id.analytic_tag_ids
        tag_ids_filtered = analytic_tag_ids.filtered(lambda tag_id: tag_id in class_dict)
        if tag_ids_filtered:
            result = class_dict[tag_ids_filtered[:1]]
        return result
