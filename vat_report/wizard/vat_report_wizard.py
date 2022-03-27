import ast
import base64
import io
import collections.abc
import datetime
from collections import defaultdict
from decimal import Decimal

from xlsxwriter.workbook import Workbook
from odoo import models, fields, api, tools, _
from odoo.osv import expression
from odoo.exceptions import UserError

DATE_FORMAT = '%d/%m/%Y'

DATE_CELL_FORMAT = 'dd/mm/yyyy'

headers_eur_cat1 = [
    ['', '', '', '', '', 'Amount in EURO', '', '', 'Amount in For. Currency', '', '', ''],
    ['Invoice date',            'Invoice number',      'Customer name',     'Description', 'Non EU Residents',                         'EU Residents',                         'VAT',           'Total',                             'Non EU Residents',                         'EU Residents',                    'Currency',           'Exchange rate'],
    ['to_date(r.invoice_date)', 'r.number_of_invoice', 'r.partner_id_name', 'a.name',      'r.credit_sign*r.amount_total_non_eu_euro', 'r.credit_sign*r.amount_total_eu_euro', '-t.balance', 'r.credit_sign*r.amount_total_euro', 'r.credit_sign*r.amount_total_non_eu_euro', 'r.credit_sign*r.amount_total_eu', 'r.currency_id.name', 'r.exchange_rate'],
    ['NONE',                    'NONE',                'NONE',              'NONE',        'sum',                                      'sum',                                  'sum',        'sum',                               'sum',                                      'sum',                             'NONE',               'NONE']
]
headers_eur_cat2 = [
    ['', '', '', '', '', 'Amount in EURO', '', '', 'Amount in For. Currency', '', '', ''],
    ['Invoice date',    'Invoice number', 'Supplier name', 'Description', 'Country of residency', 'Non EU Residents', 'EU Residents', 'Total', 'Non EU Residents', 'EU Residents', 'Currency', 'Exchange rate'],
    ['to_date(r.invoice_date)', 'r.number_of_invoice', 'r.partner_id_name', 'a.name', 'r.partner_id.country_id.name', 'r.credit_sign*r.amount_total_non_eu_euro', 'r.credit_sign*r.amount_total_eu_euro', 'r.credit_sign*r.amount_total_euro', 'r.credit_sign*r.amount_total_non_eu', 'r.credit_sign*r.amount_total_eu', 'r.currency_id.name', 'r.exchange_rate'],
    ['NONE', 'NONE', 'NONE', 'NONE', 'NONE', 'sum', 'sum', 'sum', 'sum', 'sum', 'NONE', 'NONE']
]
headers_eur_cat3 = [
    ['', '', '', '', '', 'Amount in EURO', '', '', 'Amount in For. Currency', '', '', ''],
    ['Invoice date',            'Invoice number',      'Supplier name',     'Description', 'Country of residency',         'Net',                                 'VAT',       'Gross',                                         'EU Suppliers',                    'Non EU Suppliers',                    'Currency',           'Exchange rate'],
    ['to_date(r.invoice_date)', 'r.number_of_invoice', 'r.partner_id_name', 'a.name',      'r.partner_id.country_id.name', 'r.credit_sign*r.amount_untaxed_euro', 't.balance', 'r.credit_sign*r.amount_untaxed_euro+t.balance', 'r.credit_sign*r.amount_total_eu', 'r.credit_sign*r.amount_total_non_eu', 'r.currency_id.name', 'r.exchange_rate'],
    ['NONE', 'NONE', 'NONE', 'NONE', 'NONE', 'sum', 'sum', 'sum', 'sum', 'sum', 'NONE', 'NONE']
]
headers_eur_cat4 = [
    ['', '', '', '', 'Amount in EURO', '', '', ''],
    ['Invoice date', 'Invoice number', 'Supplier name', 'Description', 'Disbursements', 'Net', 'VAT', 'Gross'],
    ['to_date(r.date)', 'r.number_of_invoice', 'r.partner_id_name', 'a.name', 'r.credit_sign*r.disbursements_amount_euro', 'r.credit_sign*r.net_amount_euro', 'r.credit_sign*r.amount_tax', 'r.credit_sign*r.amount_total_euro'],
    ['NONE', 'NONE', 'NONE', 'NONE', 'sum', 'sum', 'sum', 'sum']
]

headers_usd_cat1 = [
    ['',               '',                    '',                  '',            '',                             '',                                                    '',                 '',                      '',                  'Amount in Accounting Currency',    '',             '',            '',              '',          'Amount in Invoice Currency',         '',                  ''],
    ['Invoice date',   'Invoice number',      'Customer name',     'Description', 'Country of residency',         'Currency',                                            'ECB EUR/USD rate', 'Non EU Residents',      'EU Residents',      'Net',              'VAT',          'Gross',          'Non EU Residents',           'EU Residents',           'Net',                   'VAT',               'Gross'],
    ['r.invoice_date', 'r.number_of_invoice', 't.partner_id.name', 'a.name',      't.partner_id.country_id.name', 't.currency_id.name or t.company_id.currency_id.name', 't.exchange_rate',  't.amount_total_non_eu', 't.amount_total_eu', 't.amount_untaxed', 't.amount_tax', 't.amount_total', 't.amount_total_non_eu_euro', 't.amount_total_eu_euro', 't.amount_untaxed_curr', 't.amount_tax_curr', 't.amount_total_curr'],
    ['NONE',           'NONE',                'NONE',              'NONE',        'NONE',                         'NONE',                                                'NONE',             'sum',                   'sum',               'sum',              'sum',          'sum',            'sum',                        'sum',                    'sum',                   'sum',               'sum'],
]
headers_usd_cat2 = [
    ['',               '',                    '',                  '',            '',                             '',                                                    '',                              '',                 '',    'Amount in Accounting Currency',         '',                  '',                    '',                      '',               'Amount in Invoice Currency',          '',                      ''],
    ['Invoice date',   'Invoice number',      'Supplier name',     'Description', 'Country of residency',         'Currency',                                            'ECB EUR/USD rate', 'Non EU Residents',           'EU Residents',           'Net',                   'VAT',               'Gross',               'Non EU Residents',      'EU Residents',      'Net',              'VAT',          'Gross'],
    ['r.invoice_date', 'r.number_of_invoice', 't.partner_id.name', 'a.name',      't.partner_id.country_id.name', 't.currency_id.name or t.company_id.currency_id.name', 't.exchange_rate',  'r.amount_total_non_eu_euro', 'r.amount_total_eu_euro', 'r.amount_untaxed_euro', 'r.amount_tax_euro', 'r.amount_total_euro', 'r.amount_total_non_eu', 'r.amount_total_eu', 'r.amount_untaxed', 'r.amount_tax', 'r.amount_total'],
    ['NONE',           'NONE',                'NONE',              'NONE',        'NONE',                         'NONE',                                                'NONE',             'sum',                        'sum',                    'sum',                   'sum',               'sum',                 'sum',                   'sum',               'sum',              'sum',          'sum'],
]
headers_usd_cat3 = [
    ['',               '',                    '',                  '',            '',                             '',                                                    '',                 '',                 '',                 'Amount in Accounting Currency',              '',       '',             '',               '',               'Amount in Invoice Currency',         '',                      ''],
    ['Invoice date',   'Invoice number',      'Supplier name',     'Description', 'Country of residency',         'Currency',                                            'ECB EUR/USD rate', 'Non EU Residents',      'EU Residents',      'Net',              'VAT',          'Gross',          'Non EU Residents',           'EU Residents',           'Net',                   'VAT',               'Gross'],
    ['r.invoice_date', 'r.number_of_invoice', 't.partner_id.name', 'a.name',      't.partner_id.country_id.name', 't.currency_id.name or t.company_id.currency_id.name', 't.exchange_rate',  't.amount_total_non_eu', 't.amount_total_eu', 't.amount_untaxed', 't.amount_tax', 't.amount_total', 't.amount_total_non_eu_euro', 't.amount_total_eu_euro', 't.amount_untaxed_curr', 't.amount_tax_curr', 't.amount_total_curr'],
    ['NONE',           'NONE',                'NONE',              'NONE',        'NONE',                         'NONE',                                                'NONE',             'sum',                   'sum',               'sum',              'sum',          'sum',            'sum',                        'sum',                    'sum',                   'sum',               'sum'],
]
headers_usd_cat4 = [
    ['',               '',                    '',                  '',            '',                             '',                                                    '',                 '',                       'Amount in Accounting Currency', '', '',                                        '',                            'Amount in Invoice Currency', '',             ''],
    ['Invoice date',   'Invoice number',      'Supplier name',     'Description', 'Country of residency',         'Currency',                                            'ECB EUR/USD rate', 'Disbursements',          'Net',              'VAT',          'Gross',                                    'Disbursements',               'Net',                   'VAT',               'Gross'],
    ['r.invoice_date', 'r.number_of_invoice', 'r.partner_id.name', 'a.name',      't.partner_id.country_id.name', 't.currency_id.name or t.company_id.currency_id.name', 't.exchange_rate',  't.disbursements_amount', 't.amount_untaxed', 't.amount_tax', 't.amount_total or t.disbursements_amount', 't.disbursements_amount_euro', 't.amount_untaxed_curr', 't.amount_tax_curr', 't.amount_total_curr or t.disbursements_amount_euro'],
    ['NONE',           'NONE',                'NONE',              'NONE',        'NONE',                         'NONE',                                                'NONE',             'sum',                    'sum',              'sum',          'sum',                                      'sum',                         'sum',                   'sum',               'sum'],
]


class MultiKeyDict(collections.abc.MutableMapping):
    def __init__(self, array):
        self._storage = {}
        for keys, *values in array:
            for key in keys:
                self._storage[key] = values

    def __getitem__(self, key):
        return self._storage[self.__keytransform__(key)]

    def __setitem__(self, key, value):
        self._storage[self.__keytransform__(key)] = value

    def __delitem__(self, key):
        del self._storage[self.__keytransform__(key)]

    def __iter__(self):
        return iter(self._storage)

    def __len__(self):
        return len(self._storage)

    def __keytransform__(self, key):
        return key


class VatReportWizard(models.TransientModel):
    """Vat Report Wizard"""
    # - In a Model attribute order should be
    # === Private attributes (``_name``, ``_description``, ``_inherit``, ...)
    _name = 'vat_report_wizard'  # the model name
    _description = __doc__  # the model's informal name

    # === Default method and ``_default_get``
    @api.model
    def _get_company(self):
        return self.env.user.company_id

    _default_get_analytic_tag_ids_domain = "[('is_vat_report_analytic_tag', '=', True)]"

    @api.model
    def _default_get_analytic_tag_ids(self):
        AccountAnalyticTag = self.env['account.analytic.tag']
        tag_ids = AccountAnalyticTag.search(ast.literal_eval(self._default_get_analytic_tag_ids_domain))
        return [[6, 0, tag_ids.ids]]

    # === Field declarations
    name = fields.Char()
    date_start = fields.Date('Date Start', default=fields.Date.today)
    date_end = fields.Date('Date End', default=fields.Date.today)
    company_ids = fields.Many2many('res.company', string='Companies', required=True,
                                   default=_get_company,
                                   domain=lambda self: [('id', 'in', self.env.user.company_ids.ids)])
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags',
                                        domain=_default_get_analytic_tag_ids_domain,
                                        default=_default_get_analytic_tag_ids)
    data = fields.Binary('File', readonly=True)
    filename = fields.Char('File Name', readonly=True)
    is_paid_invoices_only = fields.Boolean('Is Paid Only', default=True)
    is_credit_notes = fields.Boolean('Credit notes')

    # === Compute, inverse and search methods in the same order as field declaration
    # === Selection method (methods used to return computed values for selection fields)
    # === Constrains methods (``@api.constrains``) and onchange methods (``@api.onchange``)
    # === CRUD methods (ORM overrides)
    # === Action methods

    # === And finally, other business methods.

    @staticmethod
    def filter_markdown(data):
        is_header1 = False
        is_header2 = False
        is_footer = False
        try:
            is_header1 = data.startswith('++') and data.endswith('++')
            is_header2 = data.startswith('**') and data.endswith('**')
            is_footer = data.startswith('__') and data.endswith('__')
            if is_header1 or is_header2 or is_footer:
                data = data[2:-2]
        except Exception as exc:
            pass
        return is_header1, is_header2, is_footer, data

    def _write_data_in_memory(self, buf, data, intro_lines_count=3):
        workbook = Workbook(buf, {'in_memory': True})

        # default cell format to size 11
        default_font_size = 10
        default_font_type = 'Calibri'
        workbook.formats[0].set_font_size(default_font_size)
        workbook.formats[0].set_font_name(default_font_type)

        worksheet = workbook.add_worksheet('VAT Report')

        if self.env.company.id == 7:
            self.set_columns_usd(worksheet)
        else:
            self.set_columns_eur(worksheet)

        header = workbook.add_format({'bold': True})
        header.set_font_size(default_font_size + 2)
        header.set_font_name(default_font_type)

        header1 = workbook.add_format({'bold': True})
        header1.set_font_size(default_font_size + 2)
        header1.set_font_name(default_font_type)
        header1.set_bg_color('#376092')
        header1.set_bottom(1)
        header1.set_top(1)
        header1.set_left(1)
        header1.set_right(1)
        header1.set_font_color('white')

        header2 = workbook.add_format({'bold': True})
        header2.set_font_size(default_font_size)
        header2.set_font_name(default_font_type)
        header2.set_bg_color('#DCE6F2')
        header2.set_bottom(1)
        header2.set_top(1)
        header2.set_left(1)
        header2.set_right(1)
        header2.set_text_wrap()
        header2.set_align('center')
        header2.set_valign('vcenter')

        footer = workbook.add_format({'bold': True})
        footer.set_font_size(default_font_size)
        footer.set_font_name(default_font_type)
        footer.set_bg_color('#FFFFCC')
        footer.set_bottom(6)
        footer.set_top(1)
        footer.set_left(1)
        footer.set_right(1)
        footer.set_align('right')

        default_format = workbook.add_format()
        default_format.set_font_size(default_font_size)
        default_format.set_font_name(default_font_type)
        default_format.set_bottom(1)
        default_format.set_top(1)
        default_format.set_left(1)
        default_format.set_right(1)

        default_format_date = workbook.add_format({'num_format': DATE_CELL_FORMAT})
        default_format_date.set_font_size(default_font_size)
        default_format_date.set_font_name(default_font_type)
        default_format_date.set_bottom(1)
        default_format_date.set_top(1)
        default_format_date.set_left(1)
        default_format_date.set_right(1)

        for row, line in enumerate(data):
            if self.env.company.id != 7:
                if len(line) > 8:
                    line.insert(8, '')
                if len(line) > 11:
                    line.insert(11, '')

            for col, item in enumerate(line):
                is_header = row < intro_lines_count
                is_header1, is_header2, is_footer, item = self.filter_markdown(item)
                if is_header:
                    cell_format = header
                elif is_header1:
                    cell_format = header1
                    if self.env.company.id != 7:
                        add_col = 13
                    else:
                        add_col = 16
                    worksheet.merge_range(row, col, row, col + add_col, 'Merged Cells', header1)
                elif is_header2:
                    cell_format = header2
                    worksheet.set_row(row, 30)
                elif is_footer:
                    cell_format = footer
                else:
                    cell_format = default_format
                try:
                    if isinstance(item, (datetime.datetime, datetime.date)):
                        worksheet.write(row, col, item, default_format_date)
                    else:
                        worksheet.write(row, col, item, cell_format)
                except Exception as exc:
                    print(line)
                    raise
        workbook.close()
        buf.seek(0)
        generated_file = buf.read()
        buf.close()
        return generated_file

    @staticmethod
    def set_columns_usd(worksheet):
        worksheet.set_column(0, 20, 24.7)  # 1.78``

    @staticmethod
    def set_columns_eur(worksheet):
        worksheet.set_column(0, 0, 10.1)
        worksheet.set_column(1, 1, 23.3)
        worksheet.set_column(2, 2, 38.6)
        worksheet.set_column(3, 3, 30.9)
        worksheet.set_column(4, 4, 12.2)
        worksheet.set_column(5, 5, 11.8)
        worksheet.set_column(6, 6, 14.4)
        worksheet.set_column(7, 7, 13.4)
        worksheet.set_column(8, 8, 16.8)
        worksheet.set_column(9, 9, 13.4)
        worksheet.set_column(10, 10, 11.8)
        worksheet.set_column(11, 11, 6.2)
        worksheet.set_column(12, 12, 7.7)
        worksheet.set_column(13, 13, 6.9)

    @staticmethod
    def convert_csv_data_to_array(csv_data):
        """
        :type csv_data: str
        :rtype: list
        """
        return [item.lstrip().split(',') for item in csv_data.splitlines(False)]

    def new_func(self):
        AccountInvoice = self.env['account.move']
        HrExpense = self.env['hr.expense']

        domain = [
            ('invoice_date', '>=', self.date_start),
            ('invoice_date', '<=', self.date_end),
        ]

        expense_domain = [
            ('date', '>=', self.date_start),
            ('date', '<=', self.date_end),
        ]

        if self.company_ids:
            append_domain = [('company_id', 'in', self.company_ids.ids)]
            domain = expression.AND([domain, append_domain])
            expense_append_domain = append_domain
            expense_domain = expression.AND([expense_domain, expense_append_domain])

        if self.analytic_tag_ids:
            append_domain = [('invoice_line_ids.analytic_tag_ids', 'in', self.analytic_tag_ids.ids)]
            domain = expression.AND([domain, append_domain])
            expense_append_domain = [('analytic_tag_ids', 'in', self.analytic_tag_ids.ids)]
            expense_domain = expression.AND([expense_domain, expense_append_domain])

        if self.is_paid_invoices_only:
            append_domain = [('state', '=ilike', 'posted')]
            domain = expression.AND([domain, append_domain])
            expense_append_domain = [('state', '=ilike', 'done')]
            expense_domain = expression.AND([expense_domain, expense_append_domain])

        record_ids = [r for r in AccountInvoice.search(domain)]
        record_ids.extend([r for r in HrExpense.search(expense_domain)])
        return record_ids

    def _prepare_data(self):
        date_start = self.date_start
        date_end = self.date_end

        record_ids = self.new_func()

        classified_invoices = defaultdict(list)
        for record_id in record_ids:
            class_of_invoice = record_id.get_class_of_invoice()
            if class_of_invoice == 'mixed_class':
                for invoice_line_id in record_id.invoice_line_ids:
                    class_of_invoice = invoice_line_id.get_class_of_invoice_line()
                    classified_invoices[class_of_invoice].append(invoice_line_id)
            else:
                classified_invoices[class_of_invoice].append(record_id)

        AccountAnalyticTag = self.env['account.analytic.tag']

        def analytic_tag_keys(cat):
            return AccountAnalyticTag.search([('vat_report_analytic_tag_category', '=ilike', cat)]).mapped('name')

        category_list = [
            (analytic_tag_keys('cat1'), 'cat1', headers_eur_cat1),
            (analytic_tag_keys('cat2'), 'cat2', headers_eur_cat2),
            (analytic_tag_keys('cat3'), 'cat3', headers_eur_cat3),
            (analytic_tag_keys('cat4'), 'cat4', headers_eur_cat4),
        ]
        category_dict = MultiKeyDict(category_list)

        def chunks(l, n):
            """Yield successive n-sized chunks from l."""
            for i in range(0, len(l), n):
                yield l[i:i + n]

        # set top header
        companies = chunks(self.company_ids.mapped('name'), 3)
        result = [[", ".join(chunk)] for chunk in companies]

        result.extend([
            ["VAT period {} to {}".format(
                *map(lambda x: fields.Date.to_date(x).strftime(DATE_FORMAT), [date_start, date_end])), ],
            [],
        ])

        def sort_func(tuple_):
            k, v = tuple_
            index_list = []
            for cc in category_list:
                for c in cc[0]:
                    index_list.append(c)
            return index_list.index(k)

        ignored_classes = ('default_class',)
        classified_invoices = ((k, v) for k, v in classified_invoices.items() if k not in ignored_classes)
        classified_invoices = sorted(classified_invoices, key=sort_func)

        def try_float(data):
            try:
                res = float(data)
            except Exception as exc:
                res = 0
            return res

        for class_of_invoice, record_ids in classified_invoices:

            category, headers_fields_funcs = category_dict.get(class_of_invoice,
                                                               headers_eur_cat1)  # noqa: W0612
            title = class_of_invoice
            pre_header = [] if len(headers_fields_funcs) == 3 else headers_fields_funcs[-4]
            header = headers_fields_funcs[-3]
            fields_names = headers_fields_funcs[-2]
            agr_funcs = headers_fields_funcs[-1]

            result.append([])
            result.append(["++{}++".format(title)])
            result.append([])
            if pre_header:
                result.append(["**{}**".format(h) for h in pre_header])
            result.append(["**{}**".format(h) for h in header])

            type_result = []
            for record_id in record_ids:
                localdict = {
                    'r': record_id,
                    'to_date': fields.Date.to_date,
                }
                line = [tools.safe_eval(field_name, localdict) or '' for field_name in fields_names]
                type_result.append(line)

            agr_line = ['' for h in header]
            for line in type_result:
                for i, agr_func in enumerate(agr_funcs):
                    if agr_func == 'sum':
                        agr_line[i] = try_float(agr_line[i]) + try_float(line[i])

            result.extend(type_result)

            def format_total_func(x):
                if isinstance(x, (int, float, Decimal)):
                    return '__{:.2f}__'.format(x)
                return '__{}__'.format(x)

            result.append(list(map(format_total_func, agr_line)))
        return result

    def _tax_group_keys(self, cat):
        AccountTaxGroup = self.env['account.tax.group']
        return AccountTaxGroup.search([('vat_report_analytic_tag_category', '=ilike', cat)]).mapped('name')

    def action_process_report_xlsx(self):
        self.ensure_one()
        options = self.env.context.get('vat_report_wizard')
        if options:
            if self.env.company.id == 7:
                data = self._usd_company_report(options)
            else:
                data = self._eur_company_report(options)
        else:
            data = self._prepare_data()
        intro_lines_count = next((i for i, item in enumerate(data) if not item), 3)
        with io.BytesIO() as buf:
            out = base64.b64encode(self._write_data_in_memory(buf, data, intro_lines_count=intro_lines_count))

        name = 'vat_report-{}'.format(fields.Date.today())
        extension = 'xlsx'
        filename = "%s.%s" % (name, extension)
        self.write({'filename': filename, 'data': out})
        if options:
            report = self.env.ref('vat_report.view_account_financial_report_export')
        else:
            report = self.env.ref('vat_report.vat_report_wizard_form')
        new_action = {
            'type': 'ir.actions.act_window',
            'res_model': 'vat_report_wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'views': [(report.id, 'form')],
            'target': 'new',
        }

        return new_action

    def _usd_company_report(self, options):
        date_start, date_end = self._get_start_end_dates(options)
        record_ids, classified_lines = self._get_records(options)
        category_list = [
            (self._tax_group_keys('cat1'), 'cat1', headers_usd_cat1),
            (self._tax_group_keys('cat2'), 'cat2', headers_usd_cat2),
            (self._tax_group_keys('cat3'), 'cat3', headers_usd_cat3),
            (self._tax_group_keys('cat4'), 'cat4', headers_usd_cat4),
        ]
        category_dict = MultiKeyDict(category_list)
        result = [[self.env.company.name]]
        result.extend([
            ["VAT period {} to {}".format(
                *map(lambda x: fields.Date.to_date(x).strftime(DATE_FORMAT), [date_start, date_end])), ],
            [],
        ])

        def sort_func(tuple_):
            k, v = tuple_
            index_list = []
            for cc in category_list:
                for c in cc[0]:
                    index_list.append(c)
            return index_list.index(k)

        classified_lines = ((k, v) for k, v in classified_lines.items())
        classified_lines = sorted(classified_lines, key=sort_func)

        def try_float(data):
            try:
                res = float(data)
            except Exception as exc:
                res = 0
            return res

        for class_of_lines, record_ids in classified_lines:
            category, headers_fields_funcs = category_dict.get(class_of_lines, headers_eur_cat1)

            title = class_of_lines
            pre_header = [] if len(headers_fields_funcs) == 3 else headers_fields_funcs[-4]
            header = headers_fields_funcs[-3]
            fields_names = headers_fields_funcs[-2]
            agr_funcs = headers_fields_funcs[-1]

            result.append([])
            result.append(["++{}++".format(title)])
            result.append([])
            if pre_header:
                result.append(["**{}**".format(h) for h in pre_header])
            result.append(["**{}**".format(h) for h in header])
            type_result = []
            for record_id in record_ids:
                move_id = record_id.move_id
                #  make available in description use account name
                try:
                    a = move_id.line_ids.filtered(
                        lambda rec: rec.account_id.internal_group in ('expense', 'income', 'asset')).account_id
                    if len(a) > 1:
                        a = a[0]
                except:
                    a = record_id.account_id
                localdict = {
                    'r': move_id,
                    'to_date': fields.Date.to_date,
                    'a': a,
                    't': record_id,
                }
                line = [tools.safe_eval(field_name, localdict) or '' for field_name in fields_names]
                type_result.append(line)

            agr_line = ['' for h in header]
            for line in type_result:
                for i, agr_func in enumerate(agr_funcs):
                    if agr_func == 'sum':
                        agr_line[i] = try_float(agr_line[i]) + try_float(line[i])

            result.extend(type_result)

            def format_total_func(x):
                if isinstance(x, (int, float, Decimal)):
                    return '__{:.2f}__'.format(x)
                return '__{}__'.format(x)

            result.append(list(map(format_total_func, agr_line)))

        return result

    def _eur_company_report(self, options):
        date_start, date_end = self._get_start_end_dates(options)
        record_ids, classified_lines = self._get_records(options)
        category_list = [
            (self._tax_group_keys('cat1'), 'cat1', headers_eur_cat1),
            (self._tax_group_keys('cat2'), 'cat2', headers_eur_cat2),
            (self._tax_group_keys('cat3'), 'cat3', headers_eur_cat3),
            (self._tax_group_keys('cat4'), 'cat4', headers_eur_cat4),
        ]
        category_dict = MultiKeyDict(category_list)

        result = [[self.env.company.name]]
        result.extend([
            ["VAT period {} to {}".format(
                *map(lambda x: fields.Date.to_date(x).strftime(DATE_FORMAT), [date_start, date_end])), ],
            [],
        ])

        def sort_func(tuple_):
            k, v = tuple_
            index_list = []
            for cc in category_list:
                for c in cc[0]:
                    index_list.append(c)
            return index_list.index(k)

        classified_lines = ((k, v) for k, v in classified_lines.items())
        classified_lines = sorted(classified_lines, key=sort_func)

        def try_float(data):
            try:
                res = float(data)
            except Exception as exc:
                res = 0
            return res

        for class_of_lines, record_ids in classified_lines:
            category, headers_fields_funcs = category_dict.get(class_of_lines, headers_eur_cat1)

            title = class_of_lines
            pre_header = [] if len(headers_fields_funcs) == 3 else headers_fields_funcs[-4]
            header = headers_fields_funcs[-3]
            fields_names = headers_fields_funcs[-2]
            agr_funcs = headers_fields_funcs[-1]

            result.append([])
            result.append(["++{}++".format(title)])
            result.append([])
            if pre_header:
                result.append(["**{}**".format(h) for h in pre_header])
            result.append(["**{}**".format(h) for h in header])
            type_result = []
            for record_id in record_ids:
                move_id = record_id.move_id
                #  make available in description use account name
                try:
                    a = move_id.line_ids.filtered(
                        lambda rec: rec.account_id.internal_group in ('expense', 'income', 'asset')).account_id
                    if len(a) > 1:
                        a = a[0]
                except:
                    a = record_id.account_id
                localdict = {
                    'r': move_id,
                    'to_date': fields.Date.to_date,
                    'a': a,
                    't': record_id,
                }
                line = [tools.safe_eval(field_name, localdict) or '' for field_name in fields_names]
                type_result.append(line)

            agr_line = ['' for h in header]
            for line in type_result:
                for i, agr_func in enumerate(agr_funcs):
                    if agr_func == 'sum':
                        agr_line[i] = try_float(agr_line[i]) + try_float(line[i])

            result.extend(type_result)

            def format_total_func(x):
                if isinstance(x, (int, float, Decimal)):
                    return '__{:.2f}__'.format(x)
                return '__{}__'.format(x)

            result.append(list(map(format_total_func, agr_line)))
        return result

    @staticmethod
    def _get_start_end_dates(options):
        date = options.get('date')
        if not date:
            raise UserWarning('Please check date options')
        date_start = date['date_from']
        date_end = date['date_to']
        return date_start, date_end,

    def _get_records(self, options):
        date_start, date_end = self._get_start_end_dates(options)
        AccountMoveLines = self.env['account.move.line']

        domain = [
            ('date', '>=', date_start),
            ('date', '<=', date_end),
        ]
        append_domain = [('company_id', '=', self.env.company.id)]
        domain = expression.AND([domain, append_domain])
        append_domain = [('tax_exigible', '=', True), ('tag_ids', '!=', False)]
        domain = expression.AND([domain, append_domain])
        is_all_entries = options.get('all_entries')
        if not is_all_entries:
            append_domain = [('parent_state', '=', 'posted')]
            domain = expression.AND([domain, append_domain])

        record_ids = [r for r in AccountMoveLines.search(domain)]

        classified_lines = defaultdict(list)
        group_id = ''
        for record_id in record_ids:
            if record_id.tax_ids:
                group_id = record_id.tax_ids[0].tax_group_id.name
            if record_id.tax_line_id:
                group_id = record_id.tax_line_id.tax_group_id.name
            if group_id:
                classified_lines[group_id].append(record_id)
            else:
                raise UserError(_("Account move line %d don't have Tax Group") % record_id.id)
        return record_ids, classified_lines
