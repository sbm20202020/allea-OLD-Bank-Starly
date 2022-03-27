# -*- coding: utf-8 -*-
# Standard libs
import math
from collections import defaultdict, namedtuple
from functools import lru_cache

import sys
from itertools import groupby
import logging
from datetime import datetime
import io

# Third party libs
from odoo import models, fields, api, _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, pycompat
from odoo.tools.misc import xlsxwriter
from odoo.tools.misc import formatLang

# Module variables init
_logger = logging.getLogger(__name__)


# class report_account_coa_inherit(models.AbstractModel):
#     _inherit = "account.coa.report"
#     filter_cash_basis = False
#     filter_all_entries = True
#     filter_hierarchy = True
#     filter_types_groups = False
#     filter_detailed_lines = False
#     filter_reversed_lines = True
#     filter_lines_without_attachment_only = False
#     filter_separate_pages_for_accounts_by_print = True
#     filter_debit_minus_credit = True
#     filter_no_80_restrict = True
#
#     # from account_report_coa.py
#     @api.model
#     def get_lines(self, options, line_id=None):
#         context = self.env.context
#         company_id = context.get('company_id') or self.env.user.company_id
#         grouped_accounts = {}
#         initial_balances = {}
#         account_move_lines = defaultdict(dict)
#         comparison_table = [options.get('date')]
#         comparison_table += options.get('comparison') and options['comparison'].get('periods') or []
#
#         #get the balance of accounts for each period
#         period_number = 0
#         for period in reversed(comparison_table):
#             # options.update(dict(unfold_all=True))
#             res = self.with_context(date_from_aml=period['date_from'], date_to=period['date_to'],
#                                     date_from=period['date_from'] and company_id.compute_fiscalyear_dates(
#                                         datetime.strptime(period['date_from'], "%Y-%m-%d"))[
#                                         'date_from'] or None,
#                                     ).group_by_account_id(options, line_id)  # Aml go back to the beginning of the user chosen range but the amount on the account line should go back to either the beginning of the fy or the beginning of times depending on the account
#             if period_number == 0:
#                 initial_balances = dict([(k, res[k]['initial_bal']['balance']) for k in res])
#             for account in res:
#                 account_move_lines[account.id][period_number] = res[account].get('lines', [])
#                 if account not in grouped_accounts:
#                     grouped_accounts[account] = [{'balance': 0, 'debit': 0, 'credit': 0} for p in comparison_table]
#                 grouped_accounts[account][period_number]['balance'] = res[account]['balance'] - res[account]['initial_bal']['balance']
#                 grouped_accounts[account][period_number]['debit'] = res[account]['debit'] - res[account]['initial_bal']['debit']
#                 grouped_accounts[account][period_number]['credit'] = res[account]['credit'] - res[account]['initial_bal']['credit']
#             period_number += 1
#
#         #build the report
#         lines = self._post_process(grouped_accounts, initial_balances, options, comparison_table)
#         if options.get('detailed_lines'):
#             options['account_move_lines'] = account_move_lines
#         return lines


# class AccountReport(models.AbstractModel):
#
#     _inherit = 'account.report'
#
#     def union_first_and_last_debit_credit_columns(self, lines):
#         currency_symbol = '€'  # FIXME: исправить в соответсвии с валютой компании self.format_value(v)?<Pavel 2018-08-31>
#
#         def convert_to_float(format_name, currency_symbol):
#             currency_symbol = self.format_value(0).replace(' ', '').replace('.', '').replace(',', '').replace('0', '')
#             if isinstance(format_name, float) or isinstance(format_name, int):
#                 return format_name
#             else:
#                 result = format_name.replace(currency_symbol, '').replace(',', '').strip()
#                 if result:
#                     result = float(result)
#                 else:
#                     result = 0
#             return result
#
#         def convert_from_float(no_format_name, currency_symbol, format_nulls=False):
#             return self.format_value_or(no_format_name, format_nulls)
#             # format_name_template = "{:,.2f} " + currency_symbol
#             # format_name_template_zero = "0 " + currency_symbol
#             # if no_format_name == 0 and not format_nulls:
#             #     return ''
#             # else:
#             #     if no_format_name == 0:
#             #         format_name_template = format_name_template_zero
#             #     return format_name_template.format(no_format_name)
#
#         def chunks(l, n=2):
#             """Yield successive n-sized chunks from l."""
#             for i in range(0, len(l), n):
#                 yield l[i:i + n]
#
#         empty_dict = {'no_format_name': 0, 'name': ''}
#         zero_dict = dict(no_format_name=0,
#                         name=self.format_value_or(0, format_nulls=True))
#         for line in lines:
#             # if line['id'] != 'grouped_accounts_total':
#             for column in line['columns']:
#                 column['no_format_name'] = column.get('no_format_name',
#                                                       convert_to_float(column['name'], currency_symbol))
#             init_debit, init_credit, *other, total_debit, total_credit = line['columns']
#             init_debit_credit_no_format_name = init_debit['no_format_name'] - init_credit['no_format_name']
#             init_debit_credit = dict(no_format_name=init_debit_credit_no_format_name,
#                                      name=convert_from_float(init_debit_credit_no_format_name, currency_symbol,
#                                                              format_nulls=True))
#             total_debit_credit_no_format_name = total_debit['no_format_name'] - total_credit['no_format_name']
#             total_debit_credit = dict(no_format_name=total_debit_credit_no_format_name,
#                                       name=convert_from_float(total_debit_credit_no_format_name, currency_symbol,
#                                                               format_nulls=True))
#
#             if line['id'] == 'grouped_accounts_total':
#                 # line['columns'] = [empty_dict, init_debit] + other + [empty_dict, total_debit]  # INFO: После совещания с Гинько <Pavel 2018-09-25>
#                 # Нули в тоталах если совпадает  # INFO: После совещания с Гинько <Pavel 2018-09-27>
#                 # oth_result = []
#                 # for d_debit, d_credit in chunks(other, 2):
#                 #     debit, credit = d_debit['no_format_name'], d_credit['no_format_name']
#                 #     if math.isclose(debit, credit):
#                 #         d_debit, d_credit = zero_dict, zero_dict
#                 #     oth_result += [d_debit, d_credit]
#                 # line['columns'] = [empty_dict, init_debit_credit] + oth_result + [empty_dict, total_debit_credit]
#                 line['columns'] = [empty_dict, init_debit_credit] + other + [empty_dict, total_debit_credit]  # INFO: После совещания с Гинько <Pavel 2018-09-28>
#             else:
#                 line['columns'] = [empty_dict, init_debit_credit] + other + [empty_dict, total_debit_credit]
#
#         return lines
#
#     def format_value(self, value, currency=False, digits=2):
#
#         if self.env.context.get('no_format'):
#             return value
#         currency_id = currency or self.env.user.company_id.currency_id
#         if currency_id.is_zero(value):
#             # don't print -0.0 in reports
#             value = abs(value)
#         res = formatLang(self.env, value, digits=digits, currency_obj=currency_id)
#         return res
#
#     def format_value_or(self, value, format_nulls=False):
#         if math.isclose(value, 0):
#             if format_nulls:
#                 return self.format_value(0) # .replace('.00', '')  # outdated TODO: добавить учёт доллара `$ 0.00` <Pavel 2018-09-17>
#             else:
#                 return ''
#         else:
#             return self.format_value(value)
#
#     #@staticmethod
#     #@lru_cache(maxsize=100)
#     def get_group_parent_list(self, group, before=None):
#         before = [group] if before is None else before
#         parent = group.parent_id
#         if parent:
#             return self.get_group_parent_list(parent, before=[parent] + before)
#         else:
#             return before
#
#     def get_group_child_list(self, parent_group):
#         """Получение имён детей от заданной родительской группы
#         :param parent_group: account.group record
#         :return: list of child_group_id.display_name
#         """
#         result = []
#         child_group_ids = self.env['account.group'].search([('parent_id.id', '=', parent_group.id)])
#         for child_group_id in child_group_ids:
#             result.append(child_group_id.display_name)
#         return result
#
#     def get_level_of_group(self, group, level=None):
#         """Получение уровня заданной группы
#         """
#         level = 1 if level is None else level
#         if group.parent_id:
#             return self.get_level_of_group(group.parent_id, level+1)
#         else:
#             return level
#
#     # Trial Balance
#     # Type          sum
#     #   111         debit-credit,debit,credit,debit-credit
#     #   222         -//-
#     #     group     sum
#     #       333     debit-credit,debit,credit,debit-credit
#     #       444     -//-
#     def create_types_groups_hierarchy(self, lines, options, html_cor_value=1):
#         """This method adds new types-groups hierarchy.
#         All the entries should be grouped in types, then all the groups inside the types.
#         As we can use the same groups in different types, we can get situation with cross-links.
#         """
#         account_move_lines = options.get('account_move_lines', {})
#         TypeInfo = namedtuple('TypeInfo', 'sequence_group, sequence, name')
#         AccountAccount = self.env['account.account']
#         groups_printed = []  # группы выведенные на экран
#         # group_children = {}  # все группы использованные при выводе отчёта
#         hierarchy_list = {}
#         current_position = 0
#         if len(lines) in (1, 0):
#             return lines
#
#         for line in lines:
#             is_grouped_by_account = line.get('caret_options') == 'account.account'
#             account_id = AccountAccount.browse(line.get('id')) if is_grouped_by_account else AccountAccount
#             group_id = account_id.group_id
#             group_id_name = group_id.display_name or 'No group'
#             type_id = account_id.user_type_id
#             type_id_name = type_id.display_name or 'No type'
#             if group_id:
#                 g_tree = [i.display_name for i in self.get_group_parent_list(group_id)]
#                 # if group_id.display_name not in group_children:
#                 #     childrens = self.get_group_child_list(group_id)
#                 #     if childrens:
#                 #         group_children[group_id.display_name] = set(self.get_group_child_list(group_id))
#             else:
#                 g_tree = []
#
#             line.update({'group_id': group_id_name,
#                          'g_id': group_id,
#                          'g_tree': g_tree,
#                          'type_id': TypeInfo(type_id.sequence_group or 10, type_id.sequence or 300, type_id_name)})
#
#         total_line = lines.pop(-1)
#         lines = sorted(lines, key=lambda x: (x['type_id'].sequence_group,
#                                              x['type_id'].sequence,
#                                              x['type_id'].name,
#                                              x['group_id'],))
#         result_lines = []
#
#         max_width = max([len(l['columns']) for l in lines]) if lines else 0
#
#         # calc sums
#         sums = dict()
#         for type_info, type_list in groupby(lines, lambda x: x['type_id']):
#             type_name = type_info.name
#             type_list = list(type_list)
#             for line in type_list:
#                 for num, column in enumerate(line['columns']):
#                     sums[type_name] = sums.get(type_name, {})
#                     sums[type_name]['sum'] = sums[type_name].get('sum', {})
#                     sums[type_name]['sum'][num] = sums[type_name]['sum'].get(num, 0)
#                     sums[type_name]['sum'][num] += column.get('no_format_name', 0)
#             type_list = sorted(type_list, key=lambda x: (-self.get_level_of_group(x['g_id']), x['group_id']))
#             for group_name, group_list in groupby(type_list, lambda x: x['group_id']):
#                 group_list = list(group_list)
#                 for line in group_list:
#                     for num, column in enumerate(line['columns']):
#                         sums[type_name] = sums.get(type_name, {})
#                         sums[type_name][group_name] = sums[type_name].get(group_name, {})
#                         sums[type_name][group_name][num] = sums[type_name][group_name].get(num, 0)
#                         sums[type_name][group_name][num] += column.get('no_format_name', 0)
#                 group_id = group_list[-1]['g_id'] if group_list else False
#                 parent_id = group_id.parent_id if group_id else False
#                 while parent_id:
#                     parent_group_name = parent_id.display_name
#                     for num in range(max_width):
#                         sums[type_name] = sums.get(type_name, {})
#                         sums[type_name][parent_group_name] = sums[type_name].get(parent_group_name, {})
#                         sums[type_name][parent_group_name][num] = sums[type_name][parent_group_name].get(num, 0)
#                         sums[type_name][parent_group_name][num] += sums[type_name][group_name][num]
#                     parent_id = parent_id.parent_id
#
#             # # get grouping sum of top groups
#             # for parent_group_name, group_with_children_name_value in group_children.items():
#             #     if len(group_with_children_name_value - sums[type_name].keys()) == 0:
#             #         for group_name in group_with_children_name_value:
#             #             for num in range(max_width):
#             #                 sums[type_name][parent_group_name] = sums[type_name].get(parent_group_name, {})
#             #                 sums[type_name][parent_group_name][num] = sums[type_name][parent_group_name].get(num, 0)
#             #                 sums[type_name][parent_group_name][num] += sums[type_name][group_name][num]
#
#         # if option then adding a detailed filter
#
#         columns_len = len(lines[0]['columns'])
#         current_position = 0
#         for type_info, type_list in groupby(lines, lambda x: x['type_id']):
#             groups_printed = []
#             type_list = list(type_list)
#             type_name = type_info.name
#             current_group_level = 1
#             current_position += 1
#             result_lines.append({'name': type_name,
#                                  'level': current_group_level,
#                                  'id': 'hierarchy_%s_%s' % (current_position, current_group_level),
#                                  'columns': [{'name': self.format_value_or(sums[type_name]['sum'].get(l, 0))} for l in range(columns_len)],
#                                  # 'class': 'o_account_reports_domain_total',
#                                  'class': 'sova_total',
#                                  })
#             if options.get('hierarchy'):
#                 for g_tree, group_list in groupby(sorted(type_list, key=lambda x: x['g_tree']),
#                                                   lambda x: x['g_tree']):
#                     group_list = list(group_list)
#                     if len(group_list) == 0:
#                         continue
#                     group_name = group_list[-1]['group_id']
#                     current_group_level = 1
#                     current_position += 1
#                     if group_name != 'No group':
#                         for g_level, g_tree_name in enumerate(g_tree[:-1], 1):
#                             current_group_level = g_level + 1
#                             if g_tree_name not in groups_printed:
#                                 result_lines.append({'name': g_tree_name,
#                                                      'level': current_group_level,
#                                                      'id': 'hierarchy_%s_%s' % (current_position, current_group_level),
#                                                      'columns': [
#                                                          {'name': self.format_value_or(sums[type_name][g_tree_name].get(l, 0),
#                                                                                        format_nulls=(l in (1, columns_len-1)))}
#                                                          for l in range(columns_len)],
#                                                      # 'class': 'sova_total_detailed_lines',
#                                                      'class': 'sova_total',
#                                                      })
#                                 current_position += 1
#                                 groups_printed.append(g_tree_name)
#
#                         current_group_level = current_group_level + 1
#                         if group_name not in groups_printed:
#                             result_lines.append({'name': group_name,
#                                                  'level': current_group_level,
#                                                  'id': 'hierarchy_%s_%s' % (current_position, current_group_level),
#                                                  'columns': [
#                                                      {'name': self.format_value_or(sums[type_name][group_name].get(l, 0),
#                                                                                    format_nulls=(l in (1, columns_len - 1)))}
#                                                      for l in range(columns_len)],
#                                                  # 'class': 'sova_total_detailed_lines',
#                                                  'class': 'sova_total',
#                                                  })
#                             current_position += 1
#                             groups_printed.append(group_name)
#                     top_level = current_group_level
#                     for line in group_list:
#                         current_group_level = top_level if group_name == 'No group' else top_level + 1
#                         current_position += 1
#                         line.update(dict(level=current_group_level if current_group_level > 1 else 1 + html_cor_value))
#                         line['class'] = 'sova_total_detailed_lines'
#                         # line['class'] = line['class'] + 'sova_total_detailed_lines' if line.get('class', '') else 'sova_total_detailed_lines'
#                         result_lines.append(line)
#                         current_group_level += 1
#                         for period_number, move_lines in sorted(account_move_lines.get(int(line['id']), {}).items()):
#                             for move_line in move_lines:
#                                 period_column = slice(2 + period_number * 2, 4 + period_number * 2)
#                                 current_position += 1
#                                 move_line_empty = {'name': ''}
#                                 move_line_empty_zero = {'name': self.format_value_or(0, format_nulls=True)}
#                                 move_line_columns = [move_line_empty] * columns_len
#                                 move_line_columns[1] = move_line_empty_zero
#                                 move_line_columns[-1] = move_line_empty_zero
#                                 move_line_columns[period_column] = [{'name': self.format_value_or(move_line.debit)},
#                                                                     {'name': self.format_value_or(move_line.credit)}]
#
#                                 result_lines.append({'name': move_line.name,
#                                                      'level': current_group_level if current_group_level > 2 else current_group_level+html_cor_value,
#                                                      'id': 'hierarchy_%s_%s' % (current_position, current_group_level),
#                                                      'columns': move_line_columns,
#                                                      # 'class': 'o_account_reports_domain_total',
#                                                      })
#             else:  # если нет группировки по иерархии
#                 for group_name, group_list in groupby(type_list, lambda x: x['group_id']):
#                     current_group_level = 2
#                     current_position += 1
#                     if group_name != 'No group':
#                         result_lines.append({'name': group_name,
#                                              'level': current_group_level,
#                                              'id': 'hierarchy_%s_%s' % (current_position, current_group_level),
#                                              'columns': [{'name': self.format_value_or(sums[type_name][group_name].get(l, 0))} for l in range(columns_len)],
#                                              # 'class': 'sova_total_detailed_lines',
#                                              'class': 'sova_total',
#                                              })
#                     for line in group_list:
#                         current_group_level = 2 if group_name == 'No group' else 3
#                         current_position += 1
#                         line.update(dict(level=current_group_level))
#                         line['class'] = 'sova_total_detailed_lines'
#                         # line['class'] = line['class'] + 'sova_total_detailed_lines' if line.get('class', '') else 'sova_total_detailed_lines'
#                         result_lines.append(line)
#                         current_group_level += 1
#                         for period_number, move_lines in sorted(account_move_lines.get(int(line['id']), {}).items()):
#                             for move_line in move_lines:
#                                 period_column = slice(2+period_number*2, 4+period_number*2)
#                                 current_position += 1
#                                 move_line_empty = {'name': ''}
#                                 move_line_empty_zero = {'name': self.format_value(0).replace('.00 ', ' ')}  # TODO: добавить учёт доллара `$ 0.00` <Pavel 2018-09-17>
#                                 move_line_columns = [move_line_empty] * columns_len
#                                 move_line_columns[1] = move_line_empty_zero
#                                 move_line_columns[-1] = move_line_empty_zero
#                                 move_line_columns[period_column] = [{'name': self.format_value_or(move_line.debit)},
#                                                                     {'name': self.format_value_or(move_line.credit)}]
#
#                                 result_lines.append({'name': move_line.name,
#                                                      'level': current_group_level,
#                                                      'id': 'hierarchy_%s_%s' % (current_position, current_group_level),
#                                                      'columns': move_line_columns,
#                                                      # 'class': 'o_account_reports_domain_total',
#                                                      })
#
#
#
#
#
#         TYPE_PREFIX= 'Type: '
#
#         '''
#         Вариант.
#         Мы на лайны мапим добавление пары user_type_id: value
#         потом сортируем все лайны по user_type_id (потом по группе, если есть) и скармливаем их уже фору.
#
#         '''
#
#
#         '''Тут еще нам необходима чистка в линиях Initial Balance и Total - одной цифрой(пусть будет дебет-кредит
#          Тоталы - просят выделить ЖЫЫЫЫРЫНМ, но это блять фронт
#
#          если нет группы, то они вровень с группой
#
#         '''
#         # for line in lines:
#         #     columns = line.get('columns', [{}])
#         #     is_grouped_by_account = line.get('caret_options') == 'account.account'
#         #     account_id = AccountAccount.browse(line.get('id')) if is_grouped_by_account else AccountAccount
#         #     group_id = account_id.group_id
#         #     if group_id:
#         #         group_prefix = group_id.code_prefix
#         #         group_name = group_id.name
#         #         group_key = group_id
#         #     else:
#         #         group_name = ''
#         #         group_prefix = account_id.group_type_code and account_id.group_type_code[0:2] or False
#         #         group_key = group_prefix
#         #
#         #     current_group_level = line.get('caret_options') == 'account.account' and 4 or line.get('level', 4)
#         #     while group_key:
#         #         # create hierarchy leaves if needed
#         #         if group_key not in hierarchy_list:
#         #             current_group_level -= 1
#         #             hierarchy_list[group_key] = {
#         #                 'position': (current_position, current_group_level),  # will be used to insert at the good place
#         #                 'values': {
#         #                     'id': 'hierarchy_%s_%s' % (current_position, current_group_level),
#         #                     'name': '%s %s' % (group_prefix, group_name) if group_prefix else group_name,
#         #                     'unfoldable': False,
#         #                     'unfolded': True,
#         #                     'parent_id': line.get('parent_id'),
#         #                 # to make these fold when the original parent gets folded
#         #                     'level': current_group_level,
#         #                     'columns': [0 for l in range(len(columns))],
#         #                 }
#         #             }
#         #
#         #         # sum line values in hierarchy leaves
#         #         hierarchy_list[group_key]['values']['columns'] = [sum(x) for x in pycompat.izip(
#         #             hierarchy_list[group_key]['values']['columns'], [c.get('no_format_name', 0) for c in columns])]
#         #
#         #         # loop on
#         #         if account_id.group_id:
#         #             group_key = group_key.parent_id
#         #             group_prefix = group_key.code_prefix
#         #             group_name = group_key.name
#         #         else:
#         #             group_prefix = group_prefix[:-2]
#         #             group_name = ''
#         #             group_key = group_prefix
#         #
#         #     # count the number of lines passed
#         #     current_position += 1
#         #
#         #     # build the final list that will be return
#         # already_inserted = 0
#         # for key in sorted(hierarchy_list, key=lambda x: hierarchy_list[x]['position']):
#         #     value = hierarchy_list[key]
#         #     value['values']['columns'] = [{'name': self.format_value(v)} for v in value['values']['columns']]
#         #     lines.insert(value['position'][0] + already_inserted, value['values'])
#         #     already_inserted += 1
#         # return lines
#         result_lines.append(total_line)
#         return result_lines
#
#     def get_html(self, options, line_id=None, additional_context=None):
#         """
#         return the html value of report, or html value of unfolded line
#         * if line_id is set, the template used will be the line_template
#         otherwise it uses the main_template. Reason is for efficiency, when unfolding a line in the report
#         we don't want to reload all lines, just get the one we unfolded.
#         """
#         caller_func = sys._getframe().f_back.f_code.co_name  # INFO: Забираем функцию, которая нас вызвала <Pavel 2018-11-13>
#         separate_pages_pdf = options.get('separate_pages_for_accounts_by_print') and (caller_func == 'get_pdf')
#         templates = self.with_context(separate_pages_for_accounts_by_print=separate_pages_pdf).get_templates()
#         report_manager = self.get_report_manager(options)
#         report = {'name': self.get_report_name(),
#                   'summary': report_manager.summary,
#                   'company_name': self.env.user.company_id.name, }
#         # if options.get('types_groups'):
#         #     options['comparison'] = options.get('comparison', {})
#         #     options['comparison']['filter'] = 'no_comparison'
#
#         lines = self.with_context(self.set_context(options)).get_lines(options, line_id=line_id)
#
#         if options.get('debit_minus_credit'):  # or options.get('hierarchy'):
#             lines = self.union_first_and_last_debit_credit_columns(lines)
#         if options.get('types_groups'):
#             # column_name = [{'name': ''},
#             #                {'name': '', 'class': 'number'},
#             #                {'name': 'Debit-Credit', 'class': 'number'},
#             #                {'name': 'Debit', 'class': 'number'},
#             #                {'name': 'Credit', 'class': 'number'},
#             #                {'name': '', 'class': 'number'},
#             #                {'name': 'Debit-Credit', 'class': 'number'}]
#             lines = self.create_types_groups_hierarchy(lines, options)
#         elif options.get('hierarchy'):
#             lines = self.create_hierarchy(lines)
#             # clear columns
#             if options.get('debit_minus_credit'):
#                 for line in lines[:-1]:
#                     if 'columns' in line and len(line['columns']) > 2:
#                         line['columns'][0]['name'] = '' if line['columns'][0]['name'] == self.format_value(0) else line['columns'][0]['name']
#                         line['columns'][-2]['name'] = '' if line['columns'][-2]['name'] == self.format_value(0) else line['columns'][-2]['name']
#
#         footnotes_to_render = []
#         if self.env.context.get('print_mode', False):
#             # we are in print mode, so compute footnote number and include them in lines values, otherwise, let the js compute the number correctly as
#             # we don't know all the visible lines.
#             footnotes = dict([(str(f.line), f) for f in report_manager.footnotes_ids])
#             number = 0
#             for line in lines:
#                 f = footnotes.get(str(line.get('id')))
#                 if f:
#                     number += 1
#                     line['footnote'] = str(number)
#                     footnotes_to_render.append({'id': f.id, 'number': number, 'text': f.text})
#
#         column_name = []
#         if options.get('debit_minus_credit'): # or options.get('hierarchy'):
#             column_name = self.get_columns_name(options)
#             column_name[1] = {'name': '', 'class': 'number'}
#             column_name[2] = {'name': '', 'class': 'number'}  #{'name': 'Debit-Credit', 'class': 'number'}
#             column_name[-2] = {'name': '', 'class': 'number'}
#             column_name[-1] = {'name': '', 'class': 'number'}  #{'name': 'Debit-Credit', 'class': 'number'}
#
#         def _get_value(amount_with_symbol=''):
#             amount_with_symbol = amount_with_symbol.replace(',', '')
#             if amount_with_symbol:
#                 value_str, symbol = amount_with_symbol.split(' ')
#                 try:
#                     value = float(value_str)
#                     currency_id = self.env['res.currency'].search([('position', '=', 'after'), ('symbol', '=', symbol)],
#                                                                   limit=1)
#                 except ValueError as exc:
#                     symbol, value_str = value_str, symbol
#                     value = float(value_str)
#                     currency_id = self.env['res.currency'].search([('position', '=', 'before'), ('symbol', '=', symbol)],
#                                                                   limit=1)
#             else:
#                 value, currency_id = 0, self.env.user.company_id.currency_id
#             return value, currency_id
#         now_model = self._context.get('model') or self.__class__.__name__
#         if now_model == 'account.general.ledger':
#             column_names = column_name or self.get_columns_name(options)
#             for i in range(len(lines)):
#                 colspan = lines[i].get('colspan', 1)
#                 currency_rate_column_number = self._list_dict_index(column_names, _("Currency Rate")) - colspan
#                 currency_amount_column_number_before_insert = self._list_dict_index(column_names, _("Currency Amount")) - colspan - 1
#                 debit_column_number_before_insert = self._list_dict_index(column_names, _("Debit")) - colspan - 1
#                 credit_column_number_before_insert = self._list_dict_index(column_names, _("Credit")) - colspan - 1
#
#                 if lines[i] and _('There are more than 80 items in this list, click here to see all of them') in lines[i]['name']:
#                     continue
#                 if lines[i] and _('Initial Balance') in lines[i]['name']:
#                     lines[i]['columns'][currency_amount_column_number_before_insert].update({'name': ''})
#                 if lines[i] and _('Total') in lines[i]['name']:
#                     lines[i]['columns'][currency_amount_column_number_before_insert].update({'name': ''})
#                 currency_amount_name = lines[i]['columns'][currency_amount_column_number_before_insert].get('name', '')
#                 currency_amount_value, amount_currency_id = _get_value(currency_amount_name)
#                 debit, debit_currency_id = _get_value(lines[i]['columns'][debit_column_number_before_insert].get('name', ''))
#                 credit, credit_currency_id = _get_value(lines[i]['columns'][credit_column_number_before_insert].get('name', ''))
#                 if lines[i].get('class', '') == 'o_account_reports_domain_total' or lines[i].get('level', 0) == 2:
#                     currency_rate_name = ''
#                     lines[i]['columns'][currency_amount_column_number_before_insert].update({'name': ''})
#                 elif not currency_amount_value:
#                     currency_rate_name = ''
#                     lines[i]['columns'][currency_amount_column_number_before_insert].update({'name': ''})
#                 else:
#                     if math.isclose(currency_amount_value, 0):
#                         currency_rate_name = ''
#                     elif debit and not credit:
#                         currency_rate_name = self.format_value(abs(currency_amount_value / debit), digits=4)
#                     elif credit:
#                         currency_rate_name = self.format_value(abs(currency_amount_value / credit), digits=4)
#                 lines[i]['columns'].insert(currency_rate_column_number, {'name': currency_rate_name.replace(debit_currency_id.symbol, '/{}'.format(debit_currency_id.symbol))})
#                 # pass
#
#         def split_iter(lines):
#             iter_lines = iter(lines)
#             buffer = [next(iter_lines)]
#             for l in iter_lines:
#                 if l.get('level') == 2:
#                     yield buffer
#                     buffer = [l]
#                 else:
#                     buffer.append(l)
#             yield buffer
#
#         lines_of_lines = []
#         if separate_pages_pdf:
#             lines_of_lines = [l for l in split_iter(lines)]
#
#         rcontext = {'report': report,
#                     'lines': {'columns_header': column_name or self.get_columns_name(options),
#                               'lines': lines, 'lines_of_lines': lines_of_lines},
#                     'options': options,
#                     'context': self.env.context,
#                     'model': self,
#                     }
#         if additional_context and type(additional_context) == dict:
#             rcontext.update(additional_context)
#         render_template = templates.get('main_template', 'account_reports.main_template')
#         if line_id is not None:
#             render_template = templates.get('line_template', 'account_reports.line_template')
#         html = self.env['ir.ui.view'].render_template(
#             render_template,
#             values=dict(rcontext),
#         )
#         if self.env.context.get('print_mode', False):
#             for k,v in self.replace_class().items():
#                 html = html.replace(k, v)
#             # append footnote as well
#             html = html.replace(b'<div class="js_account_report_footnotes"></div>', self.get_html_footnotes(footnotes_to_render))
#         return html
#
#     def _get_xlsx(self, options, response):
#         """copy with changes of enterprise `account_report.py` function"""
#         output = io.BytesIO()
#         workbook = xlsxwriter.Workbook(output, {'in_memory': True})
#         sheet = workbook.add_worksheet(self.get_report_name()[:31])
#
#         def_style = workbook.add_format({'font_name': 'Arial'})
#         title_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2})
#         super_col_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'align': 'center'})
#         level_0_style = workbook.add_format(
#             {'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2, 'pattern': 1, 'font_color': '#FFFFFF'})
#         level_0_style_left = workbook.add_format(
#             {'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2, 'left': 2, 'pattern': 1,
#              'font_color': '#FFFFFF'})
#         level_0_style_right = workbook.add_format(
#             {'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2, 'right': 2, 'pattern': 1,
#              'font_color': '#FFFFFF'})
#         level_1_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2})
#         level_1_style_left = workbook.add_format(
#             {'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2, 'left': 2})
#         level_1_style_right = workbook.add_format(
#             {'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2, 'right': 2})
#         level_2_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'top': 2, })
#         level_2_style_left = workbook.add_format({'font_name': 'Arial', 'bold': True, 'top': 2, 'left': 2, })
#         level_2_style_right = workbook.add_format({'font_name': 'Arial', 'bold': True, 'top': 2, 'right': 2, })
#         level_3_style = def_style
#         level_3_style_left = workbook.add_format({'font_name': 'Arial', 'left': 2})
#         level_3_style_right = workbook.add_format({'font_name': 'Arial', 'right': 2})
#         domain_style = workbook.add_format({'font_name': 'Arial', 'italic': True})
#         domain_style_left = workbook.add_format({'font_name': 'Arial', 'italic': True, 'left': 2})
#         domain_style_right = workbook.add_format({'font_name': 'Arial', 'italic': True, 'right': 2})
#         upper_line_style = workbook.add_format({'font_name': 'Arial', 'top': 2})
#
#         left_column_styles = (level_0_style_left, level_1_style_left, level_2_style_left, level_3_style_left,
#                               domain_style_left)
#
#         for format_ in workbook.formats:
#             format_.set_font_size(9)
#             if id(format_) not in (id(f) for f in left_column_styles):
#                 format_.set_shrink()
#
#         if options.get('types_groups'):
#             for level_style in (level_2_style, level_2_style_left, level_2_style_right):
#                 level_style.set_bg_color('#eeffcc')
#                 level_style.set_font_color('#008784')
#
#         # for i, level_style in enumerate((level_2_style_left, level_3_style_left), 1):
#         #     level_style.set_indent(i)
#
#         sheet.set_column(0, 0, 50)  # Set the first column width
#
#         super_columns = self._get_super_columns(options)
#         y_offset = bool(super_columns.get('columns')) and 1 or 0
#
#         sheet.write(y_offset, 0, '', title_style)
#
#         # Todo in master: Try to put this logic elsewhere
#         x = super_columns.get('x_offset', 0)
#         for super_col in super_columns.get('columns', []):
#             cell_content = super_col.get('string', '').replace('<br/>', ' ').replace('&nbsp;', ' ')
#             x_merge = super_columns.get('merge')
#             if x_merge and x_merge > 1:
#                 sheet.merge_range(0, x, 0, x + (x_merge - 1), cell_content, super_col_style)
#                 x += x_merge
#             else:
#                 sheet.write(0, x, cell_content, super_col_style)
#                 x += 1
#
#         column_name = []
#         if options.get('debit_minus_credit'): # or options.get('hierarchy'):
#             column_name = self.get_columns_name(options)
#             column_name[1] = {'name': '', 'class': 'number'}
#             column_name[2] = {'name': '', 'class': 'number'}  # {'name': 'Debit-Credit', 'class': 'number'}
#             column_name[-2] = {'name': '', 'class': 'number'}
#             column_name[-1] = {'name': '', 'class': 'number'}  # {'name': 'Debit-Credit', 'class': 'number'}
#             # скрытие ненужных колонок
#             col_before_debit_credit = 1
#             col_after_debit_credit = len(column_name)-2
#             sheet.set_column(col_before_debit_credit, col_before_debit_credit, None, None, {'hidden': True})
#             sheet.set_column(col_after_debit_credit, col_after_debit_credit, None, None, {'hidden': True})
#
#         x = 0
#         for column in column_name or self.get_columns_name(options):
#             sheet.write(y_offset, x, column.get('name', '').replace('<br/>', ' ').replace('&nbsp;', ' '),
#                         title_style)
#             x += 1
#         y_offset += 1
#         ctx = self.set_context(options)
#         ctx.update({'no_format': True, 'print_mode': True})
#         lines = self.with_context(ctx).get_lines(options)
#
#         if options.get('debit_minus_credit'): # or options.get('hierarchy'):
#             lines = self.union_first_and_last_debit_credit_columns(lines)
#         if options.get('types_groups'):
#             # column_name = [{'name': ''},
#             #                {'name': '', 'class': 'number'},
#             #                {'name': 'Debit-Credit', 'class': 'number'},
#             #                {'name': 'Debit', 'class': 'number'},
#             #                {'name': 'Credit', 'class': 'number'},
#             #                {'name': '', 'class': 'number'},
#             #                {'name': 'Debit-Credit', 'class': 'number'}]
#             lines = self.create_types_groups_hierarchy(lines, options, html_cor_value=0)
#         elif options.get('hierarchy'):
#             lines = self.create_hierarchy(lines)
#
#         if options.get('types_groups') or True:  # конвертирует float&int поля
#             for line in lines:
#                 for cell in line.get('columns', tuple()):
#                     if isinstance(cell.get('name', ''), (int, float)):
#                         cell['name'] = self.format_value_or(cell['name'])
#
#
#
#         if lines:
#             max_width = max([len(l['columns']) for l in lines])
#         else:
#             return None
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
#             line_level = lines[y].get('level', 0)
#             indent = '  ' * line_level if line_level>1 else ''
#             sheet.write(y + y_offset, 0, indent + lines[y]['name'], style_left)
#             for x in range(1, max_width - len(lines[y]['columns']) + 1):
#                 sheet.write(y + y_offset, x, None, style)
#             for x in range(1, len(lines[y]['columns']) + 1):
#                 # if isinstance(lines[y]['columns'][x - 1], tuple):
#                 # lines[y]['columns'][x - 1] = lines[y]['columns'][x - 1][0]
#                 if x < len(lines[y]['columns']):
#                     sheet.write(y + y_offset, x + lines[y].get('colspan', 1) - 1,
#                                 lines[y]['columns'][x - 1].get('name', ''), style)
#                 else:
#                     sheet.write(y + y_offset, x + lines[y].get('colspan', 1) - 1,
#                                 lines[y]['columns'][x - 1].get('name', ''), style_right)
#             if ('total' in lines[y].get('class', '') or lines[y].get('level') == 0) and 'sova_total' not in lines[y].get('class', ''):
#                 for x in range(len(lines[0]['columns']) + 1):
#                     sheet.write(y + 1 + y_offset, x, None, upper_line_style)
#                 y_offset += 1
#         if lines:
#             for x in range(max_width + 1):
#                 sheet.write(len(lines) + y_offset, x, None, upper_line_style)
#
#         workbook.close()
#         output.seek(0)
#         response.stream.write(output.read())
#         output.close()
#
#     def get_xlsx(self, options, response, *args, **kwargs):
#         if options.get('types_groups') or options.get('debit_minus_credit'):
#             return self._get_xlsx(options=options, response=response)
#         else:
#             return super().get_xlsx(options, response, *args, **kwargs)

