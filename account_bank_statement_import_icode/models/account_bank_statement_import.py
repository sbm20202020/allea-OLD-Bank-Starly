import logging
import base64
import io
from io import StringIO
from itertools import zip_longest
from operator import itemgetter
from zipfile import ZipFile, BadZipfile  # BadZipFile in Python >= 3.2

from datetime import date, datetime
import xlrd
from collections import OrderedDict

from odoo.tools import pycompat
from odoo import api, models, fields, _
from odoo.exceptions import Warning as UserError

_logger = logging.getLogger(__name__)


class FileImportBaseError(UserError):
    pass


class FileImportFormatError(FileImportBaseError):
    pass


class FileAlreadyImportedError(FileImportBaseError):
    pass


class ImportParamsError(FileImportBaseError):
    pass


class AccountBankStatementLine(models.Model):
    """Расширяем модель account.bank.statement.line."""
    _inherit = "account.bank.statement.line"

    unique_import_id = fields.Char('Import ID', readonly=True, copy=False)

    _sql_constraints = [
        ('unique_import_id',
         'unique (unique_import_id)',
         'A bank account transactions can be imported only once !')
    ]


class AccountBankStatementImport(models.TransientModel):
    """Расширяем модель account.bank.statement."""
    _inherit = 'account.bank.statement.import'
    _description = 'Import Bank Statement'

    def _check_csv(self, filename):
        return False  # Т.к. делаем обработку Csv сами

    @api.model
    def _get_hide_journal_field(self):
        """ Return False если journal_id отсутствует в файле
        который мы парсим и должен быть указан в визарде.
        """
        return False

    journal_id = fields.Many2one('account.journal', string='Journal',
                                 help='Accounting journal related to the bank statement you\'re '
                                      'importing. It has be be manually chosen for statement formats which '
                                      'doesn\'t allow automatic journal detection.',
                                 default=lambda self: self._get_default_journal_id())
    currency_id = fields.Many2one('res.currency', related='journal_id.currency_id', readonly=True)
    hide_journal_field = fields.Boolean(string='Hide the journal field in the view',
                                        compute='_get_hide_journal_field')
    data_file = fields.Binary('Bank Statement File', required=True,
                              help='Get you bank statements in electronic format from your bank '
                                   'and select them here.')
    filename = fields.Char()
    date_filter_start = fields.Date(string='Date filter start', required=True, default=fields.Date.today)
    date_filter_end = fields.Date(string='Date filter end', required=True, default=fields.Date.today)

    @api.model
    def _get_default_journal_id(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', [])
        return active_ids[-1]

    def import_file(self):
        """Процессим файл выбранный в визарде, создаём bank statement(s) и
        переходим к сверке."""
        self.ensure_one()
        data_file = base64.b64decode(self.data_file)

        statement_ids, notifications = self.with_context(active_id=self.id, filename=self.filename)._import_file(
            data_file)

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.bank.statement',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'current',
            'res_id': statement_ids[-1],
            'context': dict(self._context),
        }

    @api.model
    def unzip(self, data_file):
        filename = self.env.context.get('filename')
        if filename and (filename.lower().endswith(('.xlsx', '.xls', '.csv'))):
            return [data_file]
        elif filename and (filename.lower().endswith('.ofx')):
            s = data_file.decode('utf-8')
            data_file = s[s.find('<?xml'):].encode('latin-1', 'ignore')
            return data_file
        try:
            with ZipFile(StringIO(data_file), 'r') as archive:
                return [
                    archive.read(name) for name in archive.namelist()
                    if not name.endswith('/')
                ]
        except BadZipfile:
            return [data_file]

    @api.model
    def _parse_all_files(self, data_file):
        """Парсим по один файл или несколько из zip-файла.

        Возвращаем массив statements для будующей обработки.
        """
        statements = []
        files = self.unzip(data_file)
        # Парсим файл(ы)
        if isinstance(files, list):
            for import_file in files:
                new_statements = self._parse_file(import_file)
                statements += [new_statements]
        else:
            stub1, stub2 = 0, 0
            stub1, stub2, new_statements = self._parse_file(files)
            statements = new_statements
        return statements

    @api.model
    def _import_file(self, data_file):
        """ Создаем банковские statement(s) из файла."""
        # Соответствующий модуль реализации возвращает требуемые данные
        statement_ids = []
        notifications = []
        statements = self._parse_all_files(data_file)
        # Проверка исходных данных:
        self._check_parsed_data(statements)
        # Импортируем все statements:
        for stmt_vals in statements:
            (statement_id, new_notifications) = (self._import_statement(stmt_vals))
            if statement_id:
                statement_ids.append(statement_id)
            notifications.extend(new_notifications)
        if len(statement_ids) == 0:
            raise FileAlreadyImportedError(_('You have already imported that file.'))
        return statement_ids, notifications

    @api.model
    def _import_statement(self, stmt_vals):
        """импортируем единичный bank-statement.

        Возвращает ids созданных заявлений и уведомлений
        """
        currency_code = stmt_vals.pop('currency_code', '')
        account_number = stmt_vals.pop('account_number', '')
        # Пробуем найти реквизиты банковского счета и валюты в odoo
        currency_id = self._find_currency_id(currency_code)
        bank_account_id = self._find_bank_account_id(account_number)
        if not bank_account_id and account_number:
            raise UserError(
                _('Can not find the account number %s.') % account_number
            )
        # Ищем банковский журнал
        journal_id = self._get_journal(currency_id, bank_account_id)
        # К данному моменту journal и account_number должны быть известны
        if not journal_id:
            raise UserError(
                _('Can not determine journal for import'
                  ' for account number %s and currency %s.') %
                (account_number, currency_code)
            )
        # Подготавливаем statement data, которые будут использоваться для создания банковских statements
        stmt_vals = self._complete_statement(stmt_vals, journal_id, account_number)
        # Создаём банковскую stmt_vals
        return self._create_bank_statement(stmt_vals)

    # Вспомогательные функции
    @staticmethod
    def _space_strip(str_var):
        return str_var.strip(' ') if isinstance(str_var, str) else str_var

    @staticmethod
    def _convert_to_float(float_var=10.333, replace_comma=False):
        if isinstance(float_var, str):  # Python 3
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

    @staticmethod
    def _convert_to_date(date_var, datetime_format="%d/%m/%Y"):
        date_var = datetime.strptime(date_var, datetime_format)
        # fields.Datetime.to_string(date_var)
        return date_var

    @staticmethod
    def _date_to_string(date_var, datetime_format="%d/%m/%Y"):
        return date_var.strftime(datetime_format)

    @staticmethod
    def _convert_to_str():
        pass

    @api.model
    def _get_start_balance(self, journal_id):
        # FIXME Здесь мы указываем открывающий баланс по тому, который у нас сейчас в журнале. Гинько по разговору от 30/08 <Ruzki 2018-08-30>
        last_bnk_stmt = self.env['account.bank.statement'].search([('journal_id', '=', journal_id.id)], limit=1)
        if last_bnk_stmt:
            return last_bnk_stmt.balance_end
        else:
            return 0

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
                          currency_code=currency_code,
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
        date = self._convert_to_date(period.split(' - ')[-1])
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
            transaction = dict(name=r['Description'], date=r['Value Date'],
                               amount=r['Amount'],
                               # unique_import_id='',  # FIXME: добавить реализацию <Pavel 2018-08-24>
                               # account_number=account_number,
                               # currency_code=currency_code,
                               note=r['UTN'],
                               partner_name='',  # FIXME: добавить реализацию <Pavel 2018-08-24>
                               ref='')
            if date_filter_start <= r['Value Date'] <= date_filter_end:
                transactions.append(transaction)
                result_sheet.append(r)
        # balance_start = result_sheet[0]['Balance'] if result_sheet else 0

        balance_start = self._get_start_balance(self.journal_id)
        balance_end_real = result_sheet[-1]['Balance'] if result_sheet else 0

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
    def _parse_file_bank3(self, data_file):
        """["Дата", "№ документа", "ИНН контрагента", "Дебет", "Кредит", "", "Клиент", "Назначение платежа"]"""
        datetime_format = "%d.%m.%Y"
        # расположение ячеек в книге
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
                break
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

    # TODO: Как же я устал писать код на скорую руку - если кому выделят время - исправьте эту боль <Pavel 2018-10-01>
    @api.model
    def _parse_file_bank5(self, data_file):
        """["Date", "Description ", "Net Settlement Amount", "Credit", "Debit", "CCY", "Cashflow"]"""
        reader = pycompat.csv_reader(io.BytesIO(data_file), quotechar='"', delimiter=',')
        keys = list(map(self._space_strip, next(reader)))  # Getting first row

        datetime_format = "%d/%m/%Y"
        # расположение ячеек в книге

        date_filter_start = fields.Datetime.from_string(self.date_filter_start)
        date_filter_end = fields.Datetime.from_string(self.date_filter_end)

        result_sheet = []
        transactions = []
        for row in reader:
            r = OrderedDict(zip_longest(keys, map(self._space_strip, row)))
            if r['Date']:
                r['Date'] = self._convert_to_date(r['Date'], datetime_format=datetime_format)
            else:
                break
            _convert_to_float_with_comma = lambda x: self._convert_to_float(x, replace_comma=True)
            r['Credit'], r['Debit'] = list(map(_convert_to_float_with_comma, [r['Credit'], r['Debit']]))
            r['Credit'], r['Debit'] = r['Credit'], -r['Debit']
            r['Amount'] = r['Credit'] - r['Debit']
            transaction = dict(name=r['Description'], date=r['Date'],
                               amount=r['Amount'],
                               # unique_import_id='',  # FIXME: добавить реализацию <Pavel 2018-08-24>
                               # account_number=account_number,
                               # currency_code=currency_code,
                               note='',
                               partner_name='',  # FIXME: добавить реализацию <Pavel 2018-08-24>
                               ref='')
            if date_filter_start <= r['Date'] <= date_filter_end:
                transactions.append(transaction)
                result_sheet.append(r)
        # balance_start = result_sheet[0]['Balance'] if result_sheet else 0
        if result_sheet:
            pass
        else:
            raise FileImportBaseError('There is no line for import or all lines does not satisfy the filter')

        balance_start = self._get_start_balance(self.journal_id)
        balance_end_real = self._convert_to_float(result_sheet[-1]['Cashflow'],
                                                  replace_comma=True) if result_sheet else 0

        from_date = result_sheet[0]['Date']
        date_ = result_sheet[-1]['Date']
        period = list(map(self._date_to_string, (from_date, date_)))
        currency_code = max(map(itemgetter('CCY'), result_sheet))

        # FIXME: поставить текущую дату <Pavel 2018-08-24>
        statements = dict(name='statements for the period {}'.format('{} - {}'.format(*period)),
                          date=date_,
                          balance_start=balance_start,
                          balance_end_real=balance_end_real,
                          transactions=transactions,
                          # account_number=account_number,
                          currency_code=currency_code,
                          )
        return statements

    def _parse_file_csv(self, data_file):
        reader = pycompat.csv_reader(io.BytesIO(data_file), quotechar='"', delimiter=',')
        bank5_keys = list(
            map(self._space_strip, next(reader)))  # INFO: Getting first row and strip it <Pavel 2018-10-02>
        bank5_keys_standard = list(map(self._space_strip,
                                       ["Date", "Description", "Net Settlement Amount", "Credit", "Debit", "CCY",
                                        "Cashflow"]))
        try:
            if len(set(bank5_keys) & set(bank5_keys_standard)) == len(bank5_keys_standard):
                statements = self._parse_file_bank5(data_file)
            else:  # else
                raise FileImportFormatError(_('Could not make sense of the given file.'))
        except FileImportFormatError as exc:
            raise
        except Exception as exc:
            _logger.error('{}'.format(exc))
            raise FileImportFormatError(_('Could not make sense of the given file.'))
        return statements

    # TODO: забирать имена функций для каждого банка из таблицы(модели) <Pavel 2018-09-19>
    # TODO: имена функций записывать в модель рекордами(data/*.xml) <Pavel 2018-09-19>
    @api.model
    def _parse_file(self, data_file):
        """ Каждый модуль, добавляющий поддержку файлов, должен переопределять этот метод.
        Метод анализирует данный файл и возвращает данные необходимые для дальнейшего
        импорта bank statement иначе super.
        - bank statements data: list of dict содержащих (опциональные строки помечены o) :
                    - 'name': string (e.g: '000000123')
                    - 'date': date (e.g: 2013-06-26)
                    -o 'balance_start': float (e.g: 8368.56)
                    -o 'balance_end_real': float (e.g: 8888.88)
                    - 'transactions': list of dict containing :
                        - 'name': string
                            (e.g: 'KBC-INVESTERINGSKREDIET 787-5562831-01')
                        - 'date': date
                        - 'amount': float
                        - 'unique_import_id': string
                        -o account_number: string (e.g: 'BE1234567890')
                            The number of the bank account which the statement
                            belongs to
                            Will be used to find/create the res.partner.bank
                            in odoo
                        -o currency_code: string (e.g: 'EUR')
                            The ISO 4217 currency code, case insensitive
                        -o 'note': string
                        -o 'partner_name': string
                        -o 'ref': string
        """
        date_filter_start = fields.Datetime.from_string(self.date_filter_start)
        date_filter_end = fields.Datetime.from_string(self.date_filter_end)
        if date_filter_start > date_filter_end:
            raise ImportParamsError(_("End date must be greater than or equal to the start date"))

        # TODO: refactor this <Pavel 2018-10-01>
        filename = self.env.context.get('filename')
        if filename.lower().endswith('csv'):
            return self._parse_file_csv(data_file)

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

        # trying to import
        try:
            if bank1_keys == bank1_keys_standard:
                statements = self._parse_file_bank1(data_file)
            elif bank2_keys == bank2_keys_standard:
                statements = self._parse_file_bank2(data_file)
            elif bank3_keys == bank3_keys_standard:
                statements = self._parse_file_bank3(data_file)
            else:  # else
                raise FileImportFormatError(_('Could not make sense of the given file.'))
            # Пост обработка для добавление валюты из журнала
            if 'currency_code' not in statements.keys():
                statements.update(dict(currency_code=self.currency_id.name))
        except FileImportBaseError as exc:
            raise
        except Exception as exc:
            _logger.error('{}'.format(exc))
            raise FileImportFormatError(_('Could not make sense of the given file.'))
        return statements

    @api.model
    def _check_parsed_data(self, statements):
        """ Основные и структурные проверки """
        # TODO: Добавить больше логики <Pavel 2018-08-27>
        if len(statements) == 0:
            raise UserError(_('This file doesn\'t contain any statement.'))
        for stmt_vals in statements:
            if 'transactions' in stmt_vals and stmt_vals['transactions']:
                return
        # If we get here, no transaction was found:
        raise UserError(_('This file doesn\'t contain any transaction after filtering by date.'))

    @api.model
    def _find_currency_id(self, currency_code):
        """ Get res.currency ID."""
        if currency_code:
            currency_ids = self.env['res.currency'].search(
                [('name', '=ilike', currency_code)])
            if currency_ids:
                return currency_ids[0].id
            else:
                raise UserError(_(
                    'Statement has invalid currency code %s') % currency_code)
        # if no currency_code is provided, we'll use the company currency
        return self.env.user.company_id.currency_id.id

    @api.model
    def _find_bank_account_id(self, account_number):
        """ Get res.partner.bank ID """
        bank_account_id = None
        if account_number and len(account_number) > 4:
            bank_account_ids = self.env['res.partner.bank'].search(
                [('acc_number', '=', account_number)], limit=1)
            if bank_account_ids:
                bank_account_id = bank_account_ids[0].id
        return bank_account_id

    @api.model
    def _get_journal(self, currency_id, bank_account_id):
        """ Find the journal """
        bank_model = self.env['res.partner.bank']
        # Find the journal from context, wizard or bank account
        journal_id = self.env.context.get('journal_id') or self.journal_id.id
        currency = self.env['res.currency'].browse(currency_id)
        if bank_account_id:
            bank_account = bank_model.browse(bank_account_id)
            if journal_id:
                if (bank_account.journal_id.id and
                        bank_account.journal_id.id != journal_id):
                    raise UserError(
                        _('The account of this statement is linked to '
                          'another journal.'))
                if not bank_account.journal_id.id:
                    bank_model.write({'journal_id': journal_id})
            else:
                if bank_account.journal_id.id:
                    journal_id = bank_account.journal_id.id
        # If importing into an existing journal, its currency must be the same
        # as the bank statement. When journal has no currency, currency must
        # be equal to company currency.
        if journal_id and currency_id:
            journal_obj = self.env['account.journal'].browse(journal_id)
            if journal_obj.currency_id:
                journal_currency_id = journal_obj.currency_id.id
                if currency_id != journal_currency_id:
                    # ALso log message with id's for technical analysis:
                    _logger.warn(
                        _('Statement currency id is %d,'
                          ' but journal currency id = %d.'),
                        currency_id,
                        journal_currency_id
                    )
                    raise UserError(_(
                        'The currency of the bank statement (%s) is not '
                        'the same as the currency of the journal %s (%s) !'
                    ) % (
                                        currency.name,
                                        journal_obj.name,
                                        journal_obj.currency_id.name))
            else:
                company_currency = self.env.user.company_id.currency_id
                if currency_id != company_currency.id:
                    # ALso log message with id's for technical analysis:
                    _logger.warn(
                        _('Statement currency id is %d,'
                          ' but company currency id = %d.'),
                        currency_id,
                        company_currency.id
                    )
                    raise UserError(_(
                        'The currency of the bank statement (%s) is not '
                        'the same as the company currency (%s) !'
                    ) % (currency.name, company_currency.name))
        return journal_id

    @api.model
    @api.returns('res.partner.bank')
    def _create_bank_account(
            self, account_number, company_id=False, currency_id=False):
        """Automagically create bank account, when not yet existing."""
        try:
            bank_type = self.env.ref('base.bank_normal')
            bank_code = bank_type.code
        except ValueError:
            bank_code = 'bank'
        vals_acc = {
            'acc_number': account_number,
            'state': bank_code,
        }
        # Odoo users bank accounts (which we import statement from) have
        # company_id and journal_id set while 'counterpart' bank accounts
        # (from which statement transactions originate) don't.
        # Warning : if company_id is set, the method post_write of class
        # bank will create a journal
        if company_id:
            vals = self.env['res.partner.bank'].onchange_company_id(company_id)
            vals_acc.update(vals.get('value', {}))
            vals_acc['company_id'] = company_id

        # When the journal is created at same time of the bank account, we need
        # to specify the currency to use for the account.account and
        # account.journal
        return self.env['res.partner.bank'].with_context(
            default_currency_id=currency_id,
            default_currency=currency_id).create(vals_acc)

    @api.model
    def _complete_statement(self, stmt_vals, journal_id, account_number):
        """Дополняем statement с помощью предоставленной информации."""
        stmt_vals['journal_id'] = journal_id
        for line_vals in stmt_vals['transactions']:
            unique_import_id = line_vals.get('unique_import_id', False)
            if unique_import_id:
                line_vals['unique_import_id'] = (
                        (account_number and account_number + '-' or '') +
                        unique_import_id
                )
            if not line_vals.get('bank_account_id'):
                # Find the partner and his bank account or create the bank
                # account. The partner selected during the reconciliation
                # process will be linked to the bank when the statement is
                # closed.
                partner_id = False
                bank_account_id = False
                partner_account_number = line_vals.get('account_number')
                if partner_account_number:
                    bank_model = self.env['res.partner.bank']
                    banks = bank_model.search(
                        [('acc_number', '=', partner_account_number)], limit=1)
                    if banks:
                        bank_account_id = banks[0].id
                        partner_id = banks[0].partner_id.id
                    else:
                        bank_obj = self._create_bank_account(
                            partner_account_number)
                        bank_account_id = bank_obj and bank_obj.id or False
                line_vals['partner_id'] = partner_id
                line_vals['bank_account_id'] = bank_account_id
        return stmt_vals

    @api.model
    def _create_bank_statement(self, stmt_vals):
        """ Create bank statement from imported values, filtering out
        already imported transactions, and return data used by the
        reconciliation widget
        """
        bs_model = self.env['account.bank.statement']
        bsl_model = self.env['account.bank.statement.line']
        # Filter out already imported transactions and create statement
        ignored_line_ids = []
        filtered_st_lines = []
        for line_vals in stmt_vals['transactions']:
            unique_id = (
                    'unique_import_id' in line_vals and
                    line_vals['unique_import_id']
            )
            if not unique_id or not bool(bsl_model.sudo().search(
                    [('unique_import_id', '=', unique_id)], limit=1)):
                filtered_st_lines.append(line_vals)
            else:
                ignored_line_ids.append(unique_id)
        statement_id = False
        if len(filtered_st_lines) > 0:
            # Remove values that won't be used to create records
            stmt_vals.pop('transactions', None)
            for line_vals in filtered_st_lines:
                line_vals.pop('account_number', None)
            # Create the statement
            stmt_vals['line_ids'] = [
                [0, False, line] for line in filtered_st_lines]
            statement_id = bs_model.create(stmt_vals).id
        # Prepare import feedback
        notifications = []
        num_ignored = len(ignored_line_ids)
        if num_ignored > 0:
            notifications += [{
                'type': 'warning',
                'message':
                    _("%d transactions had already been imported and "
                      "were ignored.") % num_ignored
                    if num_ignored > 1
                    else _("1 transaction had already been imported and "
                           "was ignored."),
                'details': {
                    'name': _('Already imported items'),
                    'model': 'account.bank.statement.line',
                    'ids': bsl_model.search(
                        [('unique_import_id', 'in', ignored_line_ids)]).ids}
            }]
        return statement_id, notifications
