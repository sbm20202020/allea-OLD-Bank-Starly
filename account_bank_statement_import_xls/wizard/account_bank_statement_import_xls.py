# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import io
import logging
import dateutil.parser
from collections import OrderedDict
from datetime import datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError

try:
    import xlrd
except ImportError:
    xlrd = None
    logging.getLogger(__name__).warning("The xlrd python library is not installed, xlsx import will not work.")


class AccountBankStatementImport(models.TransientModel):
    _inherit = "account.bank.statement.import"

    journal_id = fields.Many2one('account.journal', string='Journal',
                                 default=lambda self: self._get_default_journal_id())

    @api.model
    def _get_default_journal_id(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', [])
        return active_ids[-1]

    def _check_xls(self, filename):
        return filename and filename.lower().strip().endswith('.xls') or filename.lower().strip().endswith('.xlsx')

    @staticmethod
    def _space_strip(str_var):
        return str_var.strip(' ') if isinstance(str_var, str) else str_var

    @staticmethod
    def _convert_to_float(float_var=10.333, replace_comma=False):
        if isinstance(float_var, str):
            float_var = float_var.strip(' ')
            float_var = float_var.replace(',', '') if replace_comma else float_var
            if float_var:
                if '.' in float_var or ',' in float_var:
                    float_var = float(float_var)
                else:
                    float_var = int(float_var)
            else:
                float_var = 0
        return float_var

    @api.model
    def _get_start_balance(self, journal_id):
        # FIXME Здесь мы указываем открывающий баланс по тому, который у нас сейчас в журнале. Гинько по разговору от 30/08 <Ruzki 2018-08-30>
        last_bnk_stmt = self.env['account.bank.statement'].search([('journal_id', '=', journal_id.id)], limit=1)
        if last_bnk_stmt:
            return last_bnk_stmt.balance_end
        else:
            return 0

    @staticmethod
    def _convert_to_date(date_var, datetime_format="%d/%m/%Y"):
        date_var = datetime.strptime(date_var, datetime_format)
        # fields.Datetime.to_string(date_var)
        return date_var

    @api.model
    def _parse_file_bank1(self, data_file):
        """['Value date', 'Reference', 'Type', 'Narrative', 'Debit', 'Credit', 'Balance']"""
        # расположение ячеек в книге
        header_row = 8
        account_number_cell = dict(rowx=2, colx=1)
        currency_code_cell = dict(rowx=3, colx=1)
        period_cell = dict(rowx=4, colx=1)
        balance_start_cell = dict(rowx=5, colx=1)
        balance_end_real_cell = dict(rowx=6, colx=1)

        book = xlrd.open_workbook(file_contents=data_file)
        sheet = book.sheet_by_index(0)
        # read header values into the list
        keys = [sheet.cell(header_row, col_index).value for col_index in range(sheet.ncols)]

        account_number = str(sheet.cell_value(**account_number_cell)).rstrip('.0')
        # FIXME Здесь мы указываем открывающий баланс по тому, который у нас сейчас в журнале. Гинько по разговору от 30/08 <Ruzki 2018-08-30>
        # balance_start = sheet.cell_value(**balance_start_cell)

        balance_start = self._get_start_balance(self.journal_id)

        balance_end_real = sheet.cell_value(**balance_end_real_cell)
        period = sheet.cell_value(**period_cell)
        date = self._convert_to_date(period.split(' - ')[-1])
        currency_code = sheet.cell_value(**currency_code_cell).split(' ')[-1]

        date_filter_start = fields.Datetime.from_string(self.date_filter_start)
        date_filter_end = fields.Datetime.from_string(self.date_filter_end)

        transactions = []
        for row_index in range(header_row + 1, sheet.nrows):
            r = OrderedDict((keys[col_index], self._space_strip(sheet.cell(row_index, col_index).value))
                            for col_index in range(sheet.ncols))
            r['Credit'], r['Debit'] = list(map(self._convert_to_float, [r['Credit'], r['Debit']]))
            r['Amount'] = r['Credit'] - r['Debit']
            r['Value date'] = self._convert_to_date(r['Value date'])
            r['Narrative'] = r['Narrative'] or r['Type']
            transaction = dict(name=r['Narrative'], date=r['Value date'],
                               amount=r['Amount'],
                               note=r['Type'],
                               partner_name='',
                               ref=r['Reference'])
            if date_filter_start <= r['Value date'] <= date_filter_end:
                transactions.append(transaction)

        # FIXME: поставить текущую дату <Pavel 2018-08-24>
        statements = dict(name='statements for the period {}'.format(period),
                          date=date,
                          balance_start=balance_start,
                          balance_end_real=balance_end_real,
                          transactions=transactions,
                          # account_number=account_number,
                          # currency_code=currency_code,
                          )
        return statements

    @api.model
    def _parse_file_bank2(self, data_file):
        """['Posting Date', 'Value Date', 'UTN', 'Description', 'Debit', 'Credit', 'Balance']"""
        # расположение ячеек в книге
        header_row = 7
        account_number_cell = dict(rowx=2, colx=1)
        currency_code_cell = dict(rowx=4, colx=1)
        period_cell = dict(rowx=5, colx=1)

        book = xlrd.open_workbook(file_contents=data_file)
        sheet = book.sheet_by_index(0)
        # read header values into the list
        keys = [sheet.cell(header_row, col_index).value for col_index in range(sheet.ncols)]

        account_number = str(sheet.cell_value(**account_number_cell)).rstrip('.0')

        period = sheet.cell_value(**period_cell)
        try:
            date = self._convert_to_date(period.split(' - ')[-1])
        except:
            raise UserError(_("Please, upload xls file in correct period"))

        currency_code = sheet.cell_value(**currency_code_cell).split(' ')[-1]

        date_filter_start = fields.Datetime.from_string(self.date_filter_start)
        date_filter_end = fields.Datetime.from_string(self.date_filter_end)

        result_sheet = []
        transactions = []
        for row_index in range(header_row + 1, sheet.nrows):
            r = OrderedDict((keys[col_index], self._space_strip(sheet.cell(row_index, col_index).value))
                            for col_index in range(sheet.ncols))
            r['Credit'], r['Debit'] = list(map(self._convert_to_float, [r['Credit'], r['Debit']]))
            r['Amount'] = r['Credit'] - r['Debit']
            r['Value Date'] = self._convert_to_date(r['Value Date'])
            transaction = {
                'name': r['Description'],
                'date': r['Value Date'],
                'amount': r['Amount'],
                # 'unique_import_id': '',  # FIXME: добавить реализацию <Pavel 2018-08-24>
                # 'account_number': account_number,
                # 'currency_code': currency_code,
                'note': r['UTN'],
                'partner_name': '',  # FIXME: добавить реализацию <Pavel 2018-08-24>
                'ref': ''
            }
            if date_filter_start <= r['Value Date'] <= date_filter_end:
                transactions.append(transaction)
                result_sheet.append(r)
        # balance_start = result_sheet[0]['Balance'] if result_sheet else 0

        balance_start = self._get_start_balance(self.journal_id)
        balance_end_real = result_sheet[-1]['Balance'] if result_sheet else 0
        if not transactions:
            raise UserError(_("Upload empty file, or change date filter lines"))
        statements = {
            'date': date,
            'name': 'statements for the period {}'.format(period),
            'balance_start': balance_start,
            'balance_end_real': balance_end_real,
            'transactions': transactions,
        }
        # FIXME: поставить текущую дату <Pavel 2018-08-24>
        return statements

    @api.model
    def _parse_file_bank3(self, data_file):
        """["Дата", "№ документа", "ИНН контрагента", "Дебет", "Кредит", "", "Клиент", "Назначение платежа"]"""
        datetime_format = "%d.%m.%Y"

        header_row = 9
        account_number_cell = dict(rowx=2, colx=0)
        period_cell = dict(rowx=3, colx=0)
        balance_end_real_cell = dict(rowx=5, colx=4)

        book = xlrd.open_workbook(file_contents=data_file)
        sheet = book.sheet_by_index(0)
        # read header values into the list
        # keys = [sheet.cell(header_row, col_index).value for col_index in range(sheet.ncols)]
        # keys = ["Дата", "№ документа", "ИНН контрагента", "Дебет", "Кредит", "", "Клиент", "Назначение платежа"]
        keys = ["Value Date", "doc_num", "ИНН контрагента", "Debit", "Credit", "nolabel", "Client",
                "Purpose of payment"]
        account_number = str(sheet.cell_value(**account_number_cell)).replace('счет:', '').strip()

        period = sheet.cell_value(**period_cell).replace(u'за период:', '').replace('с', '').strip().split(' по ')
        balance_end_real = float(sheet.cell_value(**balance_end_real_cell).replace(',', '.').replace("\xa0", ''))

        date_ = self._convert_to_date(period[-1], datetime_format=datetime_format)

        date_filter_start = fields.Datetime.from_string(self.date_filter_start)
        date_filter_end = fields.Datetime.from_string(self.date_filter_end)

        result_sheet = []
        transactions = []
        for row_index in range(header_row + 1, sheet.nrows):
            r = OrderedDict((keys[col_index], self._space_strip(sheet.cell(row_index, col_index).value))
                            for col_index in range(sheet.ncols))
            if r['Value Date']:
                r['Value Date'] = self._convert_to_date(r['Value Date'], datetime_format=datetime_format)
            else:
                continue
            r['Credit'], r['Debit'] = list(map(self._convert_to_float, [r['Credit'], r['Debit']]))
            r['Amount'] = r['Credit'] - r['Debit']
            transaction = dict(name=r['Purpose of payment'], date=r['Value Date'],
                               amount=r['Amount'],
                               # unique_import_id='',  # FIXME: добавить реализацию <Pavel 2018-08-24>
                               # account_number=account_number,
                               # currency_code=currency_code,
                               note=r['Client'],
                               partner_name='',  # FIXME: добавить реализацию <Pavel 2018-08-24>
                               ref='')
            if date_filter_start <= r['Value Date'] <= date_filter_end:
                transactions.append(transaction)
                result_sheet.append(r)
        # balance_start = result_sheet[0]['Balance'] if result_sheet else 0

        balance_start = self._get_start_balance(self.journal_id)
        # balance_end_real = result_sheet[-1]['Balance'] if result_sheet else 0

        # FIXME: поставить текущую дату <Pavel 2018-08-24>
        statements = dict(name='statements for the period {}'.format(' - '.join(period)),
                          date=date_,
                          balance_start=balance_start,
                          balance_end_real=balance_end_real,
                          transactions=transactions,
                          # account_number=account_number,
                          # currency_code=currency_code,
                          )
        return statements

    @api.model
    def _parse_file_bank4(self, data_file):
        """['№ документа', 'Дата', 'Код валюты', 'В валюте счета', '', 'В рублях', '', '', 'Курс валюты', 'Наименование контрагента', 'Назначение платежа', '', '']"""
        datetime_format = "%d.%m.%Y"

        header_row = 14
        period_cell = dict(rowx=3, colx=0)
        balance_end_real_cell = dict(rowx=6, colx=4)

        book = xlrd.open_workbook(file_contents=data_file)
        sheet = book.sheet_by_index(0)
        keys = ["Doc number", "Value Date", "Curr code", "Debit", "Credit", "Дебет", "nolabel", "Кредит", "rate", "Client",
                "Purpose of payment"]
        period = sheet.cell_value(**period_cell).replace(u'за период:', '').replace('с', '').strip().split(' по ')
        balance_end_real = float(sheet.cell_value(**balance_end_real_cell).replace(',', '.').replace("\xa0", ''))

        date_ = self._convert_to_date(period[-1], datetime_format=datetime_format)

        date_filter_start = fields.Datetime.from_string(self.date_filter_start)
        date_filter_end = fields.Datetime.from_string(self.date_filter_end)

        result_sheet = []
        transactions = []
        for row_index in range(header_row + 1, sheet.nrows):
            r = OrderedDict(
                (keys[col_index], self._space_strip(sheet.cell(row_index, col_index).value)) for col_index in range(11))
            if r['Value Date']:
                r['Value Date'] = self._convert_to_date(r['Value Date'], datetime_format=datetime_format)
            else:
                continue
            r['Credit'], r['Debit'] = list(map(self._convert_to_float, [r['Credit'], r['Debit']]))
            r['Amount'] = r['Credit'] - r['Debit']
            if r['Amount'] == 0:
                continue
            transaction = dict(name=r['Purpose of payment'], date=r['Value Date'],
                               amount=r['Amount'],
                               note=r['Client'],
                               ref='')
            if date_filter_start <= r['Value Date'] <= date_filter_end:
                transactions.append(transaction)
                result_sheet.append(r)

        balance_start = self._get_start_balance(self.journal_id)

        # FIXME: поставить текущую дату <Pavel 2018-08-24>
        statements = dict(name='statements for the period {}'.format(' - '.join(period)),
                          date=date_,
                          balance_start=balance_start,
                          balance_end_real=balance_end_real,
                          transactions=transactions,
                          )
        return statements

    def _parse_file(self, data_file):
        if not self._check_xls(self.attachment_ids.name):
            return super()._parse_file(data_file)

        if xlrd is None:
            raise UserError(_("The library 'xlrd' is missing, XLS/XLSX import cannot proceed."))

        book = xlrd.open_workbook(file_contents=data_file)
        sheet = book.sheet_by_index(0)
        # read header values into the list
        bank1_keys = [sheet.cell(8, col_index).value for col_index in range(sheet.ncols)] if sheet.nrows > 8 else []
        bank1_keys_standard = ['Value date', 'Reference', 'Type', 'Narrative', 'Debit', 'Credit', 'Balance']
        bank2_keys = [sheet.cell(7, col_index).value for col_index in range(sheet.ncols)] if sheet.nrows > 7 else []
        bank2_keys_standard = ['Posting Date', 'Value Date', 'UTN', 'Description', 'Debit', 'Credit', 'Balance']
        bank3_keys = [sheet.cell(9, col_index).value for col_index in range(sheet.ncols)] if sheet.nrows > 9 else []
        bank3_keys_standard = ['Дата', '№ документа', 'ИНН контрагента', 'Дебет', 'Кредит', '', 'Клиент',
                               'Назначение платежа']
        bank4_keys = [sheet.cell(12, col_index).value for col_index in range(sheet.ncols)] if sheet.nrows > 12 else []
        bank4_keys_standard = ['№ документа', 'Дата', 'Код валюты', 'В валюте счета', '', 'В рублях', '', '',
                               'Курс валюты', 'Наименование контрагента', 'Назначение платежа', '', '']
        vals_bank_statement = []
        account_lst = set()
        currency_lst = set()
        if bank1_keys == bank1_keys_standard:
            statements = self._parse_file_bank1(data_file)
        elif bank2_keys == bank2_keys_standard:
            statements = self._parse_file_bank2(data_file)
        elif bank3_keys == bank3_keys_standard:
            statements = self._parse_file_bank3(data_file)
        elif bank4_keys == bank4_keys_standard:
            statements = self._parse_file_bank4(data_file)
        else:
            raise UserError(_('New xls scheme of file. Please call administrator'))

        if not statements['transactions']:
            raise UserError(_("Upload empty file, or change date filter lines"))

        account_lst = None
        currency_lst = None

        return [account_lst, currency_lst, [statements]]
