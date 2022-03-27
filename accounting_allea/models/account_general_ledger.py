import calendar
import copy
import json
import io
import logging
from collections import OrderedDict

import lxml.html
import json

from odoo import models, fields, api, _
from datetime import timedelta, datetime, date
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, pycompat
from babel.dates import get_quarter_names
from odoo.tools.misc import formatLang, format_date
from odoo.tools import config
from odoo.addons.web.controllers.main import clean_action
from odoo.tools.safe_eval import safe_eval

from odoo.tools.misc import xlsxwriter

_logger = logging.getLogger(__name__)


class FakeResponse:
    def __init__(self):
        self.buff = ''

    def __getattr__(self, name):
        return self

    def write(self, buff):
        self.buff = buff


# TODO: выделить в отдельный файл <Pavel 2018-08-29>
# class AccountReport(models.AbstractModel):
#     _inherit = 'account.report'
#
#     def get_sova_options(self, options=None):
#         options = self.get_options(options)
#         # apply date and date_comparison filter
#         options = self.apply_date_filter(options)
#         options = self.apply_cmp_filter(options)
#         return options
#
#     def get_sova_xlsx(self, options, output=None, workbook=None, styles=None):  # INFO: line modified <Pavel 2018-08-29>
#         output = io.BytesIO() if output is None else output
#         workbook = xlsxwriter.Workbook(output, {'in_memory': True}) if workbook is None else workbook
#         sheet = workbook.add_worksheet(self.get_report_name()[:31])
#         if styles is None:
#             def_style = workbook.add_format({'font_name': 'Arial'})
#             title_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2})
#             level_0_style = workbook.add_format(
#                 {'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2, 'pattern': 1, 'font_color': '#FFFFFF'})
#             level_0_style_left = workbook.add_format(
#                 {'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2, 'left': 2, 'pattern': 1,
#                  'font_color': '#FFFFFF'})
#             level_0_style_right = workbook.add_format(
#                 {'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2, 'right': 2, 'pattern': 1,
#                  'font_color': '#FFFFFF'})
#             level_1_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2})
#             level_1_style_left = workbook.add_format(
#                 {'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2, 'left': 2})
#             level_1_style_right = workbook.add_format(
#                 {'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2, 'right': 2})
#             level_2_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'top': 2})
#             level_2_style_left = workbook.add_format({'font_name': 'Arial', 'bold': True, 'top': 2, 'left': 2})
#             level_2_style_right = workbook.add_format({'font_name': 'Arial', 'bold': True, 'top': 2, 'right': 2})
#             level_3_style = def_style
#             level_3_style_left = workbook.add_format({'font_name': 'Arial', 'left': 2})
#             level_3_style_right = workbook.add_format({'font_name': 'Arial', 'right': 2})
#             domain_style = workbook.add_format({'font_name': 'Arial', 'italic': True})
#             domain_style_left = workbook.add_format({'font_name': 'Arial', 'italic': True, 'left': 2})
#             domain_style_right = workbook.add_format({'font_name': 'Arial', 'italic': True, 'right': 2})
#             upper_line_style = workbook.add_format({'font_name': 'Arial', 'top': 2})
#             styles = (def_style, title_style, level_0_style, level_0_style_left, level_0_style_right, level_1_style,
#                       level_1_style_left, level_1_style_right, level_2_style, level_2_style_left, level_2_style_right,
#                       level_3_style, level_3_style_left, level_3_style_right, domain_style, domain_style_left,
#                       domain_style_right, upper_line_style)
#         else:
#             def_style, title_style, level_0_style, level_0_style_left, level_0_style_right, level_1_style, level_1_style_left, level_1_style_right, level_2_style, level_2_style_left, level_2_style_right, level_3_style, level_3_style_left, level_3_style_right, domain_style, domain_style_left, domain_style_right, upper_line_style = styles
#
#         sheet.set_column(0, 0, 15) #  Set the first column width to 15
#
#         sheet.write(0, 0, '', title_style)
#
#         y_offset = 0
#         # if self.get_report_obj().get_name() == 'coa' and self.get_special_date_line_names():
#         #     sheet.write(y_offset, 0, '', title_style)
#         #     sheet.write(y_offset, 1, '', title_style)
#         #     x = 2
#         #     for column in self.with_context(is_xls=True).get_special_date_line_names():
#         #         sheet.write(y_offset, x, column, title_style)
#         #         sheet.write(y_offset, x+1, '', title_style)
#         #         x += 2
#         #     sheet.write(y_offset, x, '', title_style)
#         #     y_offset += 1
#
#         x = 0
#         for column in self.get_columns_name(options):
#             sheet.write(y_offset, x, column.get('name', '').replace('<br/>', ' ').replace('&nbsp;', ' '), title_style)
#             x += 1
#         y_offset += 1
#         ctx = self.set_context(options)
#         ctx.update({'no_format':True, 'print_mode':True})
#         lines = self.with_context(ctx).get_lines(options)
#
#         if options.get('hierarchy'):
#             lines = self.create_hierarchy(lines)
#
#         if lines:
#             max_width = max([len(l['columns']) for l in lines])
#
#         for y in range(0, len(lines)):
#             if lines[y].get('level') == 0:
#                 for x in range(0, len(lines[y]['columns']) + 1):
#                     sheet.write(y + y_offset, x, None, upper_line_style)
#                 y_offset += 1
#                 style_left = level_0_style_left
#                 style_right = level_0_style_right
#                 style = level_0_style
#             elif lines[y].get('level') == 1:
#                 for x in range(0, len(lines[y]['columns']) + 1):
#                     sheet.write(y + y_offset, x, None, upper_line_style)
#                 y_offset += 1
#                 style_left = level_1_style_left
#                 style_right = level_1_style_right
#                 style = level_1_style
#             elif lines[y].get('level') == 2:
#                 style_left = level_2_style_left
#                 style_right = level_2_style_right
#                 style = level_2_style
#             elif lines[y].get('level') == 3:
#                 style_left = level_3_style_left
#                 style_right = level_3_style_right
#                 style = level_3_style
#             # elif lines[y].get('type') != 'line':
#             #     style_left = domain_style_left
#             #     style_right = domain_style_right
#             #     style = domain_style
#             else:
#                 style = def_style
#                 style_left = def_style
#                 style_right = def_style
#             sheet.write(y + y_offset, 0, lines[y]['name'], style_left)
#             for x in range(1, max_width - len(lines[y]['columns']) + 1):
#                 sheet.write(y + y_offset, x, None, style)
#             for x in range(1, len(lines[y]['columns']) + 1):
#                 # if isinstance(lines[y]['columns'][x - 1], tuple):
#                     # lines[y]['columns'][x - 1] = lines[y]['columns'][x - 1][0]
#                 if x < len(lines[y]['columns']):
#                     sheet.write(y + y_offset, x + lines[y].get('colspan', 1) - 1, lines[y]['columns'][x - 1].get('name', ''), style)
#                 else:
#                     sheet.write(y + y_offset, x + lines[y].get('colspan', 1) - 1, lines[y]['columns'][x - 1].get('name', ''), style_right)
#             if 'total' in lines[y].get('class', '') or lines[y].get('level') == 0:
#                 for x in range(len(lines[0]['columns']) + 1):
#                     sheet.write(y + 1 + y_offset, x, None, upper_line_style)
#                 y_offset += 1
#         if lines:
#             for x in range(max_width + 1):
#                 sheet.write(len(lines) + y_offset, x, None, upper_line_style)
#
#         return output, workbook, styles  # INFO: line added <Pavel 2018-08-29>
#
#     # for debug
#     # def get_reports_buttons(self):
#     #     buttons = super(AccountReport, self).get_reports_buttons()
#     #     return buttons+[{'name': _('print BS,CF,PL'), 'action': 'print_bscfpl'}]
#
#     @api.model
#     def get_bscfpl_xlsx(self, options):
#
#         model = 'account.financial.html.report'
#         reports = OrderedDict((
#             ('Profit and Loss', self.gen_options_for_pl),
#             ('Balance Sheet', self.gen_options_for_bs),
#             ('Cash Flow Statement', self.gen_options_for_cf),
#         ))
#         output, workbook, styles = None, None, None
#         for report_name, gen_func in reports.items():
#             report_obj = self.env[model].search([('name', '=', report_name)])
#             rep_options = report_obj.get_sova_options(copy.deepcopy(options))
#             output, workbook, styles = report_obj.get_sova_xlsx(rep_options, output=output,
#                                                                 workbook=workbook, styles=styles)
#         workbook.close()
#         output.seek(0)
#         result_workbook = output.read()
#         output.close()
#         return result_workbook
#
#     # ========================
#     # for debug
#     # ========================
#
#     def print_bscfpl(self, options):
#         result_workbook = self.get_bscfpl_xlsx()
#         with open("/media/pbk/ramdisk/excel_file{}.xlsx".format(1), "wb") as write_file:
#             write_file.write(result_workbook)
#         return {}
#
#     @api.model
#     def gen_options_for_cf(self):
#         """report: account.financial.html.report"""
#         return {'hierarchy': None, 'cash_basis': None,
#                 'comparison': {'date_from': '2018-01-01', 'string': '2018',
#                                'periods': [{'date_from': '2017-01-01', 'date_to': '2017-12-31', 'string': '2017'},
#                                            {'date_from': '2017-01-01', 'date_to': '2017-12-31', 'string': '2017'},
#                                            {'date_from': '2016-01-02', 'date_to': '2016-12-31', 'string': '2016'},
#                                            {'date_from': '2015-01-01', 'date_to': '2015-12-31', 'string': '2015'},
#                                            {'date_from': '2014-01-01', 'date_to': '2014-12-31', 'string': '2014'},
#                                            {'date_from': '2013-01-01', 'date_to': '2013-12-31', 'string': '2013'},
#                                            {'date_from': '2012-01-02', 'date_to': '2012-12-31', 'string': '2012'}],
#                                'date_to': '2017-12-31', 'filter': 'previous_period', 'number_period': 6},
#                 'date': {'date_from': '2018-01-01', 'date_to': '2018-12-31', 'filter': 'this_year', 'string': '2018'},
#                 'unfolded_lines': [], 'multi_company': [{'selected': True, 'id': 5, 'name': 'NILUFAR LIMITED'},
#                                                         {'selected': False, 'id': 1, 'name': 'OCEANICA LOGISTICS LTD'}],
#                 'all_entries': False, 'journals': None, 'unfold_all': False, 'analytic': None}
#
#     @api.model
#     def gen_options_for_bs(self):
#         """account.financial.html.report"""
#         return {'all_entries': False, 'unfolded_lines': [], 'analytic_accounts': [],
#                 'multi_company': [{'name': 'NILUFAR LIMITED', 'selected': True, 'id': 5},
#                                   {'name': 'OCEANICA LOGISTICS LTD', 'selected': False, 'id': 1}], 'hierarchy': None,
#                 'journals': None, 'analytic_tags': [], 'cash_basis': False, 'comparison': {
#                 'periods': [{'string': 'As of 07/31/2018', 'date': '2018-07-31'},
#                             {'string': 'As of 06/30/2018', 'date': '2018-06-30'},
#                             {'string': 'As of 05/31/2018', 'date': '2018-05-31'},
#                             {'string': 'As of 04/30/2018', 'date': '2018-04-30'},
#                             {'string': 'As of 03/31/2018', 'date': '2018-03-31'},
#                             {'string': 'As of 02/28/2018', 'date': '2018-02-28'},
#                             {'string': 'As of 01/31/2018', 'date': '2018-01-31'}], 'string': 'As of 07/31/2018',
#                 'filter': 'previous_period', 'number_period': 7, 'date': '2018-07-31'}, 'analytic': True,
#                 'date': {'filter': 'today', 'string': 'As of 08/29/2018', 'date': '2018-08-29'}, 'unfold_all': False}
#
#     @api.model
#     def gen_options_for_pl(self):
#         """account.financial.html.report"""
#         return {'hierarchy': None, 'multi_company': [{'id': 5, 'name': 'NILUFAR LIMITED', 'selected': True},
#                                                      {'id': 1, 'name': 'OCEANICA LOGISTICS LTD', 'selected': False}],
#                 'analytic_accounts': [], 'analytic': True, 'unfold_all': False, 'analytic_tags': [],
#                 'date': {'date_to': '2018-12-31', 'filter': 'this_year', 'date_from': '2018-01-01', 'string': '2018'},
#                 'comparison': {'periods': [{'date_to': '2017-12-31', 'date_from': '2017-01-01', 'string': '2017'},
#                                            {'date_to': '2016-12-31', 'date_from': '2016-01-02', 'string': '2016'},
#                                            {'date_to': '2015-12-31', 'date_from': '2015-01-01', 'string': '2015'},
#                                            {'date_to': '2014-12-31', 'date_from': '2014-01-01', 'string': '2014'},
#                                            {'date_to': '2013-12-31', 'date_from': '2013-01-01', 'string': '2013'},
#                                            {'date_to': '2012-12-31', 'date_from': '2012-01-02', 'string': '2012'}],
#                                'date_to': '2017-12-31', 'filter': 'previous_period', 'number_period': 6,
#                                'date_from': '2017-01-01', 'string': '2017'},
#                 'journals': [{'id': 'divider', 'name': 'NILUFAR LIMITED'},
#                              {'id': 46, 'name': 'Cash', 'code': 'CSH1', 'type': 'cash', 'selected': False},
#                              {'id': 44, 'name': 'Cash Basis Tax Journal', 'code': 'CABA', 'type': 'general',
#                               'selected': False},
#                              {'id': 40, 'name': 'Customer Invoices', 'code': 'INV', 'type': 'sale', 'selected': False},
#                              {'id': 47, 'name': 'EUROBANK EUR NILUFAR', 'code': 'BNK1', 'type': 'bank',
#                               'selected': False},
#                              {'id': 43, 'name': 'Exchange Difference', 'code': 'EXCH', 'type': 'general',
#                               'selected': False},
#                              {'id': 72, 'name': 'Loans Payable', 'code': 'LOANP', 'type': 'general', 'selected': False},
#                              {'id': 42, 'name': 'Miscellaneous Operations', 'code': 'MISC', 'type': 'general',
#                               'selected': False},
#                              {'id': 73, 'name': 'Share Capital', 'code': 'CAPIT', 'type': 'general', 'selected': False},
#                              {'id': 45, 'name': 'Stock Journal', 'code': 'STJ', 'type': 'general', 'selected': False},
#                              {'id': 41, 'name': 'Vendor Bills', 'code': 'BILL', 'type': 'purchase', 'selected': False},
#                              {'id': 'divider', 'name': 'OCEANICA LOGISTICS LTD'},
#                              {'id': 7, 'name': 'Cash', 'code': 'CSH1', 'type': 'cash', 'selected': False},
#                              {'id': 5, 'name': 'Cash Basis Tax Journal', 'code': 'CABA', 'type': 'general',
#                               'selected': False},
#                              {'id': 1, 'name': 'Customer Invoices', 'code': 'INV', 'type': 'sale', 'selected': False},
#                              {'id': 4, 'name': 'Exchange Difference', 'code': 'EXCH', 'type': 'general',
#                               'selected': False},
#                              {'id': 10, 'name': 'Loans Receivables', 'code': '01111', 'type': 'general',
#                               'selected': False},
#                              {'id': 3, 'name': 'Miscellaneous Operations', 'code': 'MISC', 'type': 'general',
#                               'selected': False},
#                              {'id': 11, 'name': 'RCB EUR OCEANICA', 'code': 'BNK1', 'type': 'bank', 'selected': False},
#                              {'id': 12, 'name': 'RCB RUB OCEANICA', 'code': 'BNK2', 'type': 'bank', 'selected': False},
#                              {'id': 8, 'name': 'RCB USD OCEANICA', 'code': 'RCBUS', 'type': 'bank', 'selected': False},
#                              {'id': 6, 'name': 'Stock Journal', 'code': 'STJ', 'type': 'general', 'selected': False},
#                              {'id': 2, 'name': 'Vendor Bills', 'code': 'BILL', 'type': 'purchase', 'selected': False}],
#                 'all_entries': False, 'cash_basis': False, 'unfolded_lines': []}


def get_class_name(x):
    return type(x).__name__


def isclassname(x, classname):
    return type(x).__name__ == classname


# class report_account_general_ledger(models.AbstractModel):
#     _inherit = "account.general.ledger"
#
#     filter_chart_accounts = []
#     filter_reversed_lines = True
#     filter_lines_without_attachment_only = True
#     filter_separate_pages_for_accounts_by_print = True
#     filter_no_80_restrict = True
#     no_80_restrict = True
#
#     def get_templates(self):
#         separate_pages_for_accounts_by_print = self._context.get('separate_pages_for_accounts_by_print')
#         templates = super().get_templates()
#         if separate_pages_for_accounts_by_print:
#             main_template = 'account_icode.template_general_ledger_report'
#             line_template = 'account_icode.line_template_general_ledger_report'
#             templates['main_template'] = main_template
#             try:
#                 self.env['ir.ui.view'].get_view_id(line_template)
#                 templates['line_template'] = line_template
#             except ValueError:
#                 pass
#         return templates
#
#     def _list_dict_index(self, list_of_dict, search_name=''):
#         if not search_name:
#             raise ValueError("Empty search_name")
#         for pos, item in enumerate(list_of_dict):
#             if isinstance(item, dict) and item.get('name', None) == search_name:
#                 return pos
#         raise ValueError('`{}` column not found'.format(search_name))
#
#     # def get_columns_name(self, options):
#     #     result = super().get_columns_name(options)
#     #     if self._name == 'account.general.ledger':
#     #         currency_column_number = self._list_dict_index(result, _("Currency"))
#     #         result[currency_column_number]['name'] = _("Currency Amount")
#     #         result.insert(currency_column_number, {'name': _("Currency Rate"), 'class': 'number'})
#     #     return result
#
#     @api.model
#     def get_lines(self, options, line_id=None):
#         """
#         origin: account_reports/models/account_general_ledger.py
#         option no_80_restrict added
#
#         """
#
#         lines = []
#         context = self.env.context
#         company_id = self.env.user.company_id
#         dt_from = options['date'].get('date_from')
#         line_id = line_id and int(line_id.split('_')[1]) or None
#         aml_lines = []
#         # Aml go back to the beginning of the user chosen range but the amount on the account line should go back to either the beginning of the fy or the beginning of times depending on the account
#         grouped_accounts = self.with_context(date_from_aml=dt_from, date_from=dt_from and company_id.compute_fiscalyear_dates(datetime.strptime(dt_from, "%Y-%m-%d"))['date_from'] or None).group_by_account_id(options, line_id)
#         sorted_accounts = sorted(grouped_accounts, key=lambda a: a.code)
#         unfold_all = context.get('print_mode') and len(options.get('unfolded_lines')) == 0
#         for account in sorted_accounts:
#             debit = grouped_accounts[account]['debit']
#             credit = grouped_accounts[account]['credit']
#             balance = grouped_accounts[account]['balance']
#             amount_currency = '' if not account.currency_id else self.format_value(grouped_accounts[account]['amount_currency'], currency=account.currency_id)
#             lines.append({
#                 'id': 'account_%s' % (account.id,),
#                 'name': account.code + " " + account.name,
#                 'columns': [{'name': v} for v in [amount_currency, self.format_value(debit), self.format_value(credit), self.format_value(balance)]],
#                 'level': 2,
#                 'unfoldable': True,
#                 'unfolded': 'account_%s' % (account.id,) in options.get('unfolded_lines') or unfold_all,
#                 'colspan': 4,
#             })
#             if 'account_%s' % (account.id,) in options.get('unfolded_lines') or unfold_all:
#                 initial_debit = grouped_accounts[account]['initial_bal']['debit']
#                 initial_credit = grouped_accounts[account]['initial_bal']['credit']
#                 initial_balance = grouped_accounts[account]['initial_bal']['balance']
#                 initial_currency = '' if not account.currency_id else self.format_value(grouped_accounts[account]['initial_bal']['amount_currency'], currency=account.currency_id)
#                 domain_lines = [{
#                     'id': 'initial_%s' % (account.id,),
#                     'class': 'o_account_reports_initial_balance',
#                     'name': _('Initial Balance'),
#                     'parent_id': 'account_%s' % (account.id,),
#                     'columns': [{'name': v} for v in ['', '', '', initial_currency, self.format_value(initial_debit), self.format_value(initial_credit), self.format_value(initial_balance)]],
#                 }]
#                 progress = initial_balance
#                 amls = amls_all = grouped_accounts[account]['lines']
#                 too_many = False
#                 if not options.get('no_80_restrict', False) and len(amls) > 80 and not context.get('print_mode'):
#                     amls = amls[:80]
#                     too_many = True
#                 used_currency = self.env.user.company_id.currency_id
#                 for line in amls:
#                     if options.get('cash_basis'):
#                         line_debit = line.debit_cash_basis
#                         line_credit = line.credit_cash_basis
#                     else:
#                         line_debit = line.debit
#                         line_credit = line.credit
#                     line_debit = line.company_id.currency_id.compute(line_debit, used_currency)
#                     line_credit = line.company_id.currency_id.compute(line_credit, used_currency)
#                     progress = progress + line_debit - line_credit
#                     currency = "" if not line.currency_id else self.with_context(no_format=False).format_value(line.amount_currency, currency=line.currency_id)
#                     name = []
#                     name = line.name and line.name or ''
#                     if line.ref:
#                         name = name and name + ' - ' + line.ref or line.ref
#                     if len(name) > 35 and not self.env.context.get('no_format'):
#                         name = name[:32] + "..."
#                     partner_name = line.partner_id.name
#                     if partner_name and len(partner_name) > 35  and not self.env.context.get('no_format'):
#                         partner_name = partner_name[:32] + "..."
#                     caret_type = 'account.move'
#                     if line.invoice_id:
#                         caret_type = 'account.move.in' if line.invoice_id.type in ('in_refund', 'in_invoice') else 'account.move.out'
#                     elif line.payment_id:
#                         caret_type = 'account.payment'
#                     line_value = {
#                         'id': line.id,
#                         'caret_options': caret_type,
#                         'parent_id': 'account_%s' % (account.id,),
#                         'name': line.move_id.name if line.move_id.name else '/',
#                         'columns': [{'name': v} for v in [format_date(self.env, line.date), name, partner_name, currency,
#                                     line_debit != 0 and self.format_value(line_debit) or '',
#                                     line_credit != 0 and self.format_value(line_credit) or '',
#                                     self.format_value(progress)]],
#                         'level': 4,
#                     }
#                     aml_lines.append(line.id)
#                     domain_lines.append(line_value)
#                 domain_lines.append({
#                     'id': 'total_' + str(account.id),
#                     'class': 'o_account_reports_domain_total',
#                     'parent_id': 'account_%s' % (account.id,),
#                     'name': _('Total '),
#                     'columns': [{'name': v} for v in ['', '', '', amount_currency, self.format_value(debit), self.format_value(credit), self.format_value(balance)]],
#                 })
#                 if too_many:
#                     domain_lines.append({
#                         'id': 'too_many' + str(account.id),
#                         'parent_id': 'account_%s' % (account.id,),
#                         'name': _('There are more than 80 items in this list, click here to see all of them'),
#                         'colspan': 7,
#                         'columns': [{}],
#                         'action': 'view_too_many',
#                         'action_id': 'account,%s' % (account.id,),
#                     })
#                 lines += domain_lines
#
#         journals = [j for j in options.get('journals') if j.get('selected')]
#         if len(journals) == 1 and journals[0].get('type') in ['sale', 'purchase'] and not line_id:
#             total = self._get_journal_total()
#             lines.append({
#                 'id': 0,
#                 'class': 'total',
#                 'name': _('Total'),
#                 'columns': [{'name': v} for v in ['', '', '', '', self.format_value(total['debit']), self.format_value(total['credit']), self.format_value(total['balance'])]],
#                 'level': 1,
#                 'unfoldable': False,
#                 'unfolded': False,
#             })
#             lines.append({
#                 'id': 0,
#                 'name': _('Tax Declaration'),
#                 'columns': [{'name': v} for v in ['', '', '', '', '', '', '']],
#                 'level': 1,
#                 'unfoldable': False,
#                 'unfolded': False,
#             })
#             lines.append({
#                 'id': 0,
#                 'name': _('Name'),
#                 'columns': [{'name': v} for v in ['', '', '', '', _('Base Amount'), _('Tax Amount'), '']],
#                 'level': 2,
#                 'unfoldable': False,
#                 'unfolded': False,
#             })
#             for tax, values in self._get_taxes(journals[0]).items():
#                 lines.append({
#                     'id': '%s_tax' % (tax.id,),
#                     'name': tax.name + ' (' + str(tax.amount) + ')',
#                     'caret_options': 'account.tax',
#                     'unfoldable': False,
#                     'columns': [{'name': v} for v in ['', '', '', '', values['base_amount'], values['tax_amount'], '']],
#                     'level': 4,
#                 })
#
#         if self.env.context.get('aml_only', False):
#             return aml_lines
#         return lines
#
#
#     @api.model
#     def get_options(self, previous_options=None):
#         if self.filter_analytic:
#             self.filter_chart_accounts = [] if self.filter_analytic else None
#
#         self.filter_no_80_restrict = True if self.no_80_restrict else None
#
#         return super().get_options(previous_options)
#
#     def set_context(self, options):
#         """This method will set information inside the context based on the options dict as some options need to be in context for the query_get method defined in account_move_line"""
#         ctx = super().set_context(options)
#         if options.get('chart_accounts'):
#             ctx['chart_accounts'] = self.env['account.account'].browse([int(acc) for acc in options['chart_accounts']])
#         return ctx
#
#     def get_whole_reversion_chain(self, chain_head, whole_chain=None):
#         whole_chain = [] if whole_chain is None else whole_chain
#
#         if chain_head.reversal_of_id != 0:
#             chain_next_part = self.env['account.move.line'].search([('id', '=', chain_head.reversal_of_id)])
#             if chain_next_part:
#                 return self.get_whole_reversion_chain(chain_next_part, whole_chain + [chain_head])
#             else:
#                 return whole_chain + [chain_head]
#         else:
#             return whole_chain + [chain_head]
#
#     # 293 line
#     # grouped_accounts[account]['lines'] = [l for l in grouped_accounts[account]['lines'] if l.reversal_of_id==0 and l.reversed_by_id==0]
#     def group_by_account_id(self, options, line_id):
#         """ удаляем реверсивные строки если включена соответствующая опция"""
#         company_id = self.env.user.company_id
#         dt_from = options['date'].get('date_from')
#         if not dt_from:
#             dt_from = str(datetime.today().date())
#         accounts = super(report_account_general_ledger, self.with_context(date_from_aml=dt_from, date_from=dt_from and company_id.compute_fiscalyear_dates(datetime.strptime(dt_from, "%Y-%m-%d"))['date_from'] or None)).group_by_account_id(options, line_id)
#
#         if options.get('chart_accounts'):
#             # FIXME перенести в наш .py <Ruzki 2018-09-27>
#             filtered_accounts = list(map(int, options.get('chart_accounts')))
#             if len(filtered_accounts):  # просто на всякий случай
#                 accounts = {k: v for k, v in accounts.items() if k.id in filtered_accounts}
#
#         if options.get('reversed_lines'):
#             for account_id, values in accounts.items():
#                 _logger.info(account_id.display_name)
#                 if isclassname(values['lines'], 'account.move.line'):
#                     debit_credit_list = [[r['debit'], r['credit']] for r in values['lines'].filtered(lambda r: (r.reversal_of_id != 0 or r.reversed_by_id != 0) and not r.last_odd_reverse)]
#                     debit, credit = zip(*debit_credit_list) if debit_credit_list else [[0], [0]]
#                     values['lines'] = values['lines'].filtered(lambda r: (r.reversal_of_id == 0 and r.reversed_by_id == 0) or r.last_odd_reverse)
#                     # мы исключаем из выборки записи,где all((reversal_of_id, reversed_by_id))
#                     accounts[account_id]['debit'] -= sum(debit)
#                     accounts[account_id]['credit'] -= sum(credit)
#
#                     #values['debit'] -= sum(debit)
#                     #values['credit'] -= sum(credit)
#                     values['balance'] = values['debit'] - values['credit']
#
#         if options.get('lines_without_attachment_only'):
#
#             def has_attachments(record):
#                 res_model = get_class_name(record.move_id)  # 'account.move.line'
#                 IrAttachment = self.env['ir.attachment']
#                 if record:
#                     attachment_count = IrAttachment.search_count(
#                         [('res_model', '=', res_model), ('res_id', '=', record.move_id.id)])
#                     return attachment_count > 0
#                 return False
#
#             for account_id, values in accounts.items():
#                 _logger.info(account_id.display_name)
#                 if isclassname(values['lines'], 'account.move.line'):
#
#                     debit_credit_list = [[r['debit'], r['credit']] for r in values['lines'].filtered(lambda r: has_attachments(r))]
#                     debit, credit = zip(*debit_credit_list) if debit_credit_list else [[0], [0]]
#                     values['lines'] = values['lines'].filtered(lambda r: not has_attachments(r))
#                     # мы исключаем из выборки записи,где all((reversal_of_id, reversed_by_id))
#                     accounts[account_id]['debit'] -= sum(debit)
#                     accounts[account_id]['credit'] -= sum(credit)
#
#                     #values['debit'] -= sum(debit)
#                     #values['credit'] -= sum(credit)
#                     values['balance'] = values['debit'] - values['credit']
#
#         chains = []
#         for chain_head in self.env['account.move.line'].search(['&', ('reversal_of_id', '!=', 0), ('reversed_by_id', '=', 0)]):
#             chains.append(self.get_whole_reversion_chain(chain_head))
#             if len(chains[-1]) % 2:
#                 for chain in chains[-1][:-1]:
#                     # chain.last_odd_reverse = False
#                     pass
#                 # chains[-1][-1].last_odd_reverse = True
#
#         return accounts
#
#
#     def get_report_informations(self, options):
#         # if not options['date']['date_from']:
#         #     options['date']['date_from'] = date.today()
#         info = super().get_report_informations(options)
#         if options and options.get('analytic') is not None:
#             searchview_dict = {'options': options, 'context': self.env.context}
#
#             searchview_dict['analytic_accounts'] = self.env.user.id in self.env.ref(
#                 'analytic.group_analytic_accounting').users.ids and [(t.id, t.name) for t in
#                                                                      self.env['account.analytic.account'].search(
#                                                                          [])] or False
#             searchview_dict['analytic_tags'] = self.env.user.id in self.env.ref(
#                 'analytic.group_analytic_accounting').users.ids and [(t.id, t.name) for t in
#                                                                      self.env['account.analytic.tag'].search(
#                                                                          [])] or False
#             searchview_dict['chart_accounts'] = self.env.user.id in self.env.ref(
#                 'analytic.group_analytic_accounting').users.ids and [
#                                                     (t.id, '{} {} ({})'.format(t.code, t.name, t.company_id.name))
#                                                     for t in
#                                                     self.env['account.account'].search(
#                                                         [])] or False
#
#
#             info.update({'searchview_html': self.env['ir.ui.view'].render_template(self.get_templates().get('search_template', 'account_report.search_template'), values=searchview_dict)})
#
#         return info
