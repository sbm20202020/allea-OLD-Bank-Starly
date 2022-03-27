from contextlib import suppress

from odoo import models, fields, api, tools


class AccountInvoice(models.Model):
    """Extend account move fields to sum .. """
    _inherit = 'account.move'
    # Default methods
    # Fields declaration
    amount_tax_euro = fields.Monetary(string='Total', readonly=True, compute='_compute_euro_amounts')
    amount_untaxed_euro = fields.Monetary(string='Total', readonly=True, compute='_compute_euro_amounts')
    amount_total_euro = fields.Monetary(string='Total', readonly=True, compute='_compute_euro_amounts')
    amount_total_non_eu = fields.Monetary(string='Total', readonly=True, compute='_compute_eu_non_eu_amounts')
    amount_total_eu = fields.Monetary(string='Total', readonly=True, compute='_compute_eu_non_eu_amounts')
    amount_total_eu_euro = fields.Monetary(string='Total', readonly=True, compute='_compute_eu_non_eu_amounts')
    amount_total_non_eu_euro = fields.Monetary(string='Total', readonly=True, compute='_compute_eu_non_eu_amounts')
    article_11b = fields.Char(string='Article 11b', compute='_compute_article_11b')
    credit_sign = fields.Float(compute='_compute_credit_sign')
    disbursements_amount = fields.Monetary(compute='_compute_disbursements_vat_net_amounts')
    disbursements_amount_euro = fields.Monetary(compute='_compute_disbursements_vat_net_amounts_euro')
    exchange_rate = fields.Float('Exchange Rate', compute='_compute_exchange_rate')
    net_amount = fields.Monetary(compute='_compute_disbursements_vat_net_amounts')
    net_amount_euro = fields.Monetary(compute='_compute_disbursements_vat_net_amounts_euro')
    number_of_invoice = fields.Char(compute='_compute_number_of_invoice')
    partner_id_name = fields.Char(related='partner_id.name')
    vat_amount = fields.Monetary(compute='_compute_disbursements_vat_net_amounts')
    vat_amount_euro = fields.Monetary(compute='_compute_disbursements_vat_net_amounts_euro')

    # Compute and search fields, in the same order of fields declaration
    def _compute_euro_amounts(self):
        for invoice_id in self:
            invoice_currency_id = invoice_id.currency_id
            company_currency_id = invoice_id.company_currency_id
            invoice_id.amount_tax_euro = invoice_currency_id._convert(invoice_id.amount_tax,
                                                                      company_currency_id,
                                                                      invoice_id.company_id,
                                                                      invoice_id.date)
            invoice_id.amount_untaxed_euro = invoice_currency_id._convert(invoice_id.amount_untaxed,
                                                                          company_currency_id,
                                                                          invoice_id.company_id,
                                                                          invoice_id.date)
            invoice_id.amount_total_euro = invoice_currency_id._convert(invoice_id.amount_total,
                                                                        company_currency_id,
                                                                        invoice_id.company_id,
                                                                        invoice_id.date)
            # invoice_id.amount_tax_euro = company_currency_id.compute(invoice_id.amount_tax, invoice_currency_id)
            # invoice_id.amount_untaxed_euro = company_currency_id.compute(invoice_id.amount_untaxed, invoice_currency_id)
            # invoice_id.amount_total_euro = company_currency_id.compute(invoice_id.amount_total, invoice_currency_id)

    @api.depends('partner_id.is_in_eu')
    def _compute_eu_non_eu_amounts(self):
        for invoice_id in self:
            if invoice_id.partner_id.is_in_eu:
                invoice_id.amount_total_eu = invoice_id.amount_untaxed
                invoice_id.amount_total_eu_euro = invoice_id.amount_untaxed_euro
                invoice_id.amount_total_non_eu = 0
                invoice_id.amount_total_non_eu_euro = 0
            else:
                invoice_id.amount_total_eu = 0
                invoice_id.amount_total_eu_euro = 0
                invoice_id.amount_total_non_eu = invoice_id.amount_untaxed
                invoice_id.amount_total_non_eu_euro = invoice_id.amount_untaxed_euro

    def _compute_article_11b(self):
        for invoice_id in self:
            for analytic_tag_id_name in invoice_id.invoice_line_ids.mapped('analytic_tag_ids').mapped('name'):
                if analytic_tag_id_name == 'Article 11b':
                    invoice_id.article_11b = '11b'
                    break
            else:
                invoice_id.article_11b = ''

    def _compute_exchange_rate(self):
        for invoice_id in self:
            exchange_rate = 0.0
            with suppress(ZeroDivisionError):
                exchange_rate = abs(invoice_id.amount_total / invoice_id.amount_total_euro)
            invoice_id.exchange_rate = tools.float_round(exchange_rate, precision_digits=4)

    def _compute_credit_sign(self):
        credit_note_types = ('out_refund', 'in_refund')
        for invoice_id in self:
            if invoice_id.type in credit_note_types:
                invoice_id.credit_sign = -1
            else:
                invoice_id.credit_sign = 1

    def _compute_disbursements_vat_net_amounts(self):
        for invoice_id in self:
            if invoice_id.amount_tax:
                invoice_id.disbursements_amount = 0
                invoice_id.vat_amount = invoice_id.amount_tax
                invoice_id.net_amount = invoice_id.amount_untaxed
            else:
                invoice_id.disbursements_amount = invoice_id.amount_total
                invoice_id.vat_amount = 0
                invoice_id.net_amount = 0
                invoice_id.amount_total_eu = invoice_id.amount_total

    def _compute_disbursements_vat_net_amounts_euro(self):
        currency_euro = self.env.ref('base.EUR')
        for invoice_id in self:
            invoice_currency_id = invoice_id.currency_id.with_context(date=invoice_id.invoice_date)
            invoice_id.disbursements_amount_euro = invoice_currency_id.compute(invoice_id.disbursements_amount,
                                                                               currency_euro)
            invoice_id.vat_amount_euro = invoice_currency_id.compute(invoice_id.vat_amount, currency_euro)
            invoice_id.net_amount_euro = invoice_currency_id.compute(invoice_id.net_amount, currency_euro)

    def _compute_number_of_invoice(self):
        for invoice_id in self:
            if invoice_id.type in ('in_invoice',):
                invoice_id.number_of_invoice = invoice_id.ref
            else:
                invoice_id.number_of_invoice = invoice_id.name

    # Constraints and onchanges
    # CRUD methods (and name_get, name_search, ...) overrides
    # Action methods
    # Business methods

    @api.model
    def get_class_dict(self):
        class_dict = {}
        account_analytic_tags = self.env['account.analytic.tag'].search([('is_vat_report_analytic_tag', '=', True)])
        for analytic_tag_id in account_analytic_tags:
            class_name = analytic_tag_id.name
            class_dict[class_name] = analytic_tag_id
        reverse_class_dict = {v: k for k, v in class_dict.items() if k is not None}
        return reverse_class_dict

    @staticmethod
    def all_same(items):
        """Checks that all items in list is the same"""
        return all(x == items[0] for x in items)

    def get_class_of_invoice(self):
        self.ensure_one()
        invoice_id = self
        class_dict = self.get_class_dict()
        result = 'default_class'
        invoice_line_ids = invoice_id.invoice_line_ids
        line_tags = []
        for invoice_line_id in invoice_line_ids:
            analytic_tag_ids = invoice_line_id.analytic_tag_ids
            tag_ids_filtered = analytic_tag_ids.filtered(lambda tag_id: tag_id in class_dict)
            if tag_ids_filtered:
                line_tags.append(tag_ids_filtered)
        if invoice_line_ids:
            if self.all_same(line_tags):
                result = class_dict[line_tags[0][:1]]
            else:
                result = 'mixed_class'
        return result
