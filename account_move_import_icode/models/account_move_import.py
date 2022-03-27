# -*- coding: utf-8 -*-
"""Импорт move statement файлов"""
import base64
import io
import logging
from collections import OrderedDict
from datetime import datetime
from io import StringIO
from itertools import zip_longest
from operator import itemgetter
from zipfile import ZipFile, BadZipfile  # BadZipFile in Python >= 3.2
from itertools import groupby

import xlrd

from odoo import api, models, fields
from odoo.exceptions import Warning as UserError
from odoo.tools import pycompat
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class FileImportBaseError(UserError):
    pass


class FileImportFormatError(FileImportBaseError):
    pass


class FileAlreadyImportedError(FileImportBaseError):
    pass


class ImportParamsError(FileImportBaseError):
    pass


# class AccountMove(models.Model):
#
#     _inherit = "account.move"
#
#     @api.model
#     def create(self, vals):
#         move = super(AccountMove, self.with_context(check_move_validity=False, partner_id=vals.get('partner_id'))).create(vals)
#         # move.assert_balanced()
#         return move
#     # unique_import_id = fields.Char('Import ID', readonly=True, copy=False)
#     #
#     # _sql_constraints = [
#     #     ('unique_import_id',
#     #      'unique (unique_import_id)',
#     #      'A move account move entry can be imported only once !')
#     # ]



class AccountMovesImport(models.TransientModel):
    """Расширяем модель account.move.statement."""
    _name = 'account.move.statement.import'
    _description = 'Import Move Statement'

    def _check_csv(self, filename):
        return False  # Т.к. делаем обработку Csv сами

    @api.model
    def _get_hide_journal_field(self):
        """ Return False если journal_id отсутствует в файле
        который мы парсим и должен быть указан в визарде.
        """
        return False

    journal_id = fields.Many2one('account.journal', string='Journal',
                                 help='Accounting journal related to the move statement you\'re '
                                 'importing. It has be be manually chosen for statement formats which '
                                 'doesn\'t allow automatic journal detection.',
                                 default=lambda self: self._get_default_journal_id())

    company_id = fields.Many2one('res.company', string='Company', related='journal_id.company_id')
    currency_id = fields.Many2one('res.currency', related='journal_id.currency_id', readonly=True)
    hide_journal_field = fields.Boolean(string='Hide the journal field in the view',
                                        compute='_get_hide_journal_field')
    data_file = fields.Binary('Moves File', required=True,
                              help='Moves file should be prepared as for given rules ')
    # TODO Правила составления csv файла <Ruzki 2018-10-05>

    filename = fields.Char()

    date_filter_start = fields.Date(string='Date filter start', required=True,
                                    default=lambda *a: fields.Datetime.to_string(fields.Datetime.from_string(fields.Datetime.now()).replace(year=2016, month=1, day=1)))
    date_filter_end = fields.Date(string='Date filter end', required=True,
                                  default=lambda *a: fields.Datetime.to_string(fields.Datetime.from_string(fields.Datetime.now()).replace(year=fields.Datetime.from_string(fields.Datetime.now()).year+1)))


    @api.model
    def _get_default_journal_id(self):
        context = dict(self._context or {})
        active_model = context.get('active_model', False)
        active_ids = context.get('active_ids', [])
        return active_ids[-1]

    def import_file(self):
        """Процессим файл выбранный в визарде, создаём move statement(s) и
        переходим к сверке."""
        self.ensure_one()
        data_file = base64.b64decode(self.data_file)

        move_ids, notifications = self.with_context(active_id=self.id,
                                                         filename=self.filename,
                                                         # date_filter_start=self.date_filter_start,
                                                         # date_filter_end=self.date_filter_end
                                                         )._import_file(data_file)

        #creation of Journal Moves

        # statement_id = self.env['account.move.statement'].create(dict(journal_id=journal_id))

        # action = self.env.ref('account.action_move_statement_tree')
        return {
            'name': _('Imported Moves'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', move_ids)],
        }


    @api.model
    def unzip(self, data_file):
        filename = self.env.context.get('filename')
        if filename and (filename.lower().endswith(('.xlsx', '.xls', '.csv'))):
            return [data_file]
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
        for import_file in files:
            # Соответсвующие модули возвращяют statements.
            new_statements = self._parse_file(import_file)
            statements += new_statements
        return statements

    @api.model
    def _import_file(self, data_file):
        """ Create moves(!!!!)."""

        move_ids = []
        notifications = []
        statements = self._parse_all_files(data_file)
        # Проверка исходных данных:
        self._check_parsed_data(statements)
        # Импортируем все statements:
        for stmt_vals in statements:
            (move_id, new_notifications) = (self._import_statement(stmt_vals))
            if move_id:
                move_ids.append(move_id)
            notifications.extend(new_notifications)
        # if len(move_ids) == 0:
        #     raise FileAlreadyImportedError(_('You have already imported that file.'))
        return move_ids, notifications

    @api.model
    def _import_statement(self, stmt_vals):
        """импортируем единичный move-statement.
        """
        currency_code = stmt_vals.pop('currency_code', '') # на всякий
        stmt_vals['journal_id'] = self.journal_id.id
        # stmt_vals = self._complete_statement(stmt_vals, self.journal_id.id)

        return self._create_move_statement(stmt_vals)

    # Вспомогательные функции
    @staticmethod
    def _space_strip(str_var):
        return str_var.strip(' ') if isinstance(str_var, str) else str_var

    @staticmethod
    def _convert_to_float(float_var, replace_comma=False):
        if isinstance(float_var, str):  # Python 3
            float_var = float_var.strip(' ')
            float_var = float_var.strip(' ') # пробел из файла импорта
            if ' ' in float_var:
                float_var = float_var.replace(' ', '')
            # проверяем, нет ли у нас СОВЕРШЕННО случайно запятых как разделителей десятичных знаков
            if len(float_var) >= 3 and ('.' in float_var or ',' in float_var):
                if float_var.rfind(',') > float_var.rfind('.'): # по ходу . правее - это и есть наш разделитель точек
                    float_var = float_var.replace(',', '.')
                else:
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
        last_bnk_stmt = self.env['account.move.statement'].search([('journal_id', '=', journal_id.id)], limit=1)
        if last_bnk_stmt:
            return last_bnk_stmt.balance_end
        else:
            return 0




    @classmethod
    def _check_datetime_format(cls, datetime_string, FORMATS_TO_CHECK=['%d.%m.%Y', '%d/%m/%Y', '%m/%d/%Y']):
        """
        Полууниверсальная функция проверки формата дат. не избавляет от ошибки на самом деле

        для 01/01/2018 результат формата будет первым из списка форматов ((

        :param datetime_string:
        :param FORMATS_TO_CHECK:
        :return:
        """
        for f in FORMATS_TO_CHECK:
            try:
                date = cls._convert_to_date(datetime_string, datetime_format=f)
                return f
            except:
                continue
        return

    def get_objects_if_exists(self, search_sequence, obj_names, model_name, field_name, check_company=False):
        '''
        Function return ID of Many2one field if object extists

        :param search_sequence: named tuple or dict
        :param obj_name: list of key names like 'Partner'
        :param model_name: odoo model name to search like 'res.partner'
        :param field_name: odoo field name in model like 'name'
        :param check_company: if True - we check company_id in model and current user
        :return: int id or False
        '''
        obj_ids = []
        for obj_name in obj_names:
            if search_sequence.get(obj_name, False):
                domain = [(field_name, 'ilike', search_sequence.get(obj_name, False))]
                if check_company:
                    domain.append(('company_id', '=', self.env.user.company_id.id))
                obj = self.env[model_name].search(domain, limit=1)
                if obj:
                    obj_ids.append(obj.id)
        return obj_ids

    def convert_through_rate(self, amount_currency, currency_id_id, transaction_date):
        currency_rate = self.env['res.currency.rate'].search(
            [('company_id', '=', self.company_id.id), ('currency_id', '=', currency_id_id), ('name', '=', transaction_date)])
        if currency_rate:
            return round(amount_currency / currency_rate.rate, 2)

        return 0




    @api.model
    def _parse_file_move_enumerate(self, data_file, columns_rule):
        """["Date	Account Code	Label	Partner	Analytic Account	Analytic Tags	Amount Currency	Currency Code	Debit	Credit "]"""
        reader = pycompat.csv_reader(io.BytesIO(data_file), quotechar='"', delimiter=',')
        keys = list(map(self._space_strip, next(reader))) # Getting first row
        datetime_format = None
        account_ids = self.env['account.account'].search([('company_id', '=', self.company_id.id)])

        account_codes = {a.code:a.id for a in account_ids}

        date_filter_start = fields.Datetime.from_string(self.date_filter_start)
        date_filter_end = fields.Datetime.from_string(self.date_filter_end)

        result_sheet = []
        transactions = []
        missed_accounts = []

        for row in reader:

            r = OrderedDict(zip_longest(keys, map(self._space_strip, row)))
            if r['Date']:
                # пока изменение формата даты КАЖДЫЙ раз
                # if not datetime_format:
                datetime_format = self._check_datetime_format(r['Date'])
                r['Date'] = self._convert_to_date(r['Date'], datetime_format=datetime_format)
            else:
                break
            _convert_to_float_with_comma = lambda x: self._convert_to_float(x, replace_comma=True)
            r['Credit'], r['Debit'], r['Amount Currency'] = list(map(_convert_to_float_with_comma, [r.get('Credit', 0), r.get('Debit', 0), r.get('Amount Currency', 0)]))
            #r['Credit'], r['Debit'] = r['Credit'], r['Debit']
            currency_id_id = next(iter(self.get_objects_if_exists(r, ['Currency Code'], 'res.currency', 'name')), False)
            if not r['Credit'] and not r['Debit'] and r['Amount Currency']:
                # r_date = datetime.today()
                #

                if r['Amount Currency'] > 0:
                    r['Debit'] = self.convert_through_rate(r['Amount Currency'], currency_id_id, r['Date'])
                else:
                    r['Credit'] = - self.convert_through_rate(r['Amount Currency'], currency_id_id, r['Date'])

            r['Amount'] = r['Debit'] - r['Credit']
            account_code_id = account_codes.get(r['Account Code'], None)
            if not account_code_id:
                missed_accounts.append(r['Account Code'])
                continue

            analytic_tags_list = list(map(lambda x: x.strip(),  r['Analytic Tags'].split(';')))
            if analytic_tags_list:
                analytic_tags_list_ids = self.env['account.analytic.tag'].search([('name', 'in', analytic_tags_list)])

            transaction = dict(name=r['Label'],
                               r_move_date=r['Date'],
                               # amount=r['Amount'],
                               debit=r['Debit'],
                               credit=r['Credit'],
                               # unique_import_id='',  # FIXME: добавить реализацию <Pavel 2018-08-24>
                               account_id=account_code_id,
                               currency_id=currency_id_id,
                               # note='',
                               analytic_account_id=next(iter(self.get_objects_if_exists(r, ['Analytic Account',], 'account.analytic.account', 'name', check_company=True)), False),
                               analytic_tag_ids=[(6,0,analytic_tags_list_ids.ids)],
                               partner_id=next(iter(self.get_objects_if_exists(r, ['Partner',], 'res.partner', 'name')), False),
                               amount_currency=r.get('Amount Currency', 0),
                               )
            if date_filter_start <= r['Date'] <= date_filter_end:
                transactions.append(transaction)
                result_sheet.append(r)
        # balance_start = result_sheet[0]['Balance'] if result_sheet else 0
        if result_sheet:
            pass
        elif missed_accounts:
            raise FileImportBaseError(
                'There are no accounts for moves import. We miss accounts with code(s): {}'.format(
                    ', '.join(sorted(set(missed_accounts)))))
        else:
            raise FileImportBaseError('There is no line for import or all lines does not satisfy the filter')

        # ------------------------------------

        res_statements = []
        moves_import_debug = False

        try:
            moves_import_debug = self.env['ir.config_parameter'].sudo().get_param('moves_import_debug',
                                                                                  False).lower() != 'false'
            pass
        except:
            moves_import_debug = self.env['ir.config_parameter'].sudo().get_param('moves_import_debug',
                                                                                  False)
        for key, trans_by_date in groupby(sorted(transactions, key=lambda k: k['r_move_date']), lambda k: k['r_move_date']):


            balance_start = self._get_start_balance(self.journal_id)
            # balance_end_real = self._convert_to_float(result_sheet[-1]['Cashflow'], replace_comma=True) if result_sheet else 0
            balance_end_real = 0

            # from_date = result_sheet[0]['Date']
            # date_ = result_sheet[-1]['Date']
            # period = list(map(self._date_to_string, (from_date, date_)))
            # currency_code = max(map(itemgetter('Currency'), result_sheet))

            statements = dict(name='Import dd. {}'.format(fields.Datetime.now()[:10]),
                              date=key,
                              transactions=list(trans_by_date),
                              # account_number=account_number,
                              # currency_code=currency_code,
                              )


            if moves_import_debug:
                _logger.info('Moves Import. Debit: {}'.format(sum(t['debit'] for t in statements['transactions'])))
                _logger.info('Moves Import. Credit: {}'.format(sum(t['credit'] for t in statements['transactions'])))


                difference = sum(t['debit'] for t in statements['transactions']) - sum(t['credit'] for t in statements['transactions'])

                if difference:

                    # account_code = '510206000' if difference <= 0 else '220403000'
                    account_code = '510206000'
                    if not account_codes.get(account_code, False):
                        raise FileImportBaseError(
                            'You are in difference correction mode, but you have no difference account {} for current company. Import is stopped.'.format(account_code))
                    diff_transaction = dict(name='Difference',
                                       debit=-difference if difference <= 0 else 0,
                                       credit=difference if difference > 0 else 0,
                                       account_id=account_codes[account_code],
                                       # currency_id=currency_id_id,
                                       )

                    statements['transactions'].append(diff_transaction)

            res_statements.append(statements)
            if not moves_import_debug and missed_accounts:
                raise FileImportBaseError('We are missing some Accounts in your Chart Of Account. There are no accounts with code(s): {}'.format(', '.join(sorted(set(missed_accounts)))))
        return res_statements


    def _parse_file_csv(self, data_file):
        reader = pycompat.csv_reader(io.BytesIO(data_file), quotechar='"', delimiter=',')
        move_keys = list(map(self._space_strip, next(reader)))  # INFO: Getting first row and strip it <Pavel 2018-10-02>
        # move5_keys_standard = list(map(self._space_strip, ["Date", "Account Code", "Description", "Net Settlement Amount", "Credit", "Debit", "Currency", "Cashflow"]))
        move_keys_standard = list(map(self._space_strip,
                                       ['Date', 'Account Code', 'Label', 'Partner', 'Analytic Account', 'Analytic Tags', 'Amount Currency', 'Currency Code', 'Debit', 'Credit']))



        clean_keys = []
        for idx, key in enumerate(move_keys):
            if key in move_keys_standard:
                clean_keys.append((idx, key))
        if not len(clean_keys) == len(move_keys_standard):
            raise FileImportFormatError(_('Could not make sense of the given file.'))

        try:
            statements = self._parse_file_move_enumerate(data_file, clean_keys)
        except FileImportFormatError as exc:
            raise
        except FileImportBaseError as exc:
            raise
        except Exception as exc:
            _logger.error('{}'.format(exc))
            raise FileImportFormatError(_('Could not make sense of the given file.'))
        return statements


    @api.model
    def _parse_file(self, data_file):
        """ Каждый модуль, добавляющий поддержку файлов, должен переопределять этот метод.
        Метод анализирует данный файл и возвращает данные необходимые для дальнейшего
        импорта move statement иначе super.
        - move statements data: list of dict содержащих (опциональные строки помечены o) :
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
                            The number of the move account which the statement
                            belongs to
                            Will be used to find/create the res.partner.move
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
        else:
            raise FileImportFormatError(_('Could not make sense of the given file.'))

        # book = xlrd.open_workbook(file_contents=data_file)
        # sheet = book.sheet_by_index(0)
        # # read header values into the list
        # move1_keys = [sheet.cell(8, col_index).value for col_index in range(sheet.ncols)]
        # move1_keys_standard = ['Value date', 'Reference', 'Type', 'Narrative', 'Debit', 'Credit', 'Balance']
        # move2_keys = [sheet.cell(7, col_index).value for col_index in range(sheet.ncols)]
        # move2_keys_standard = ['Posting Date', 'Value Date', 'UTN', 'Description', 'Debit', 'Credit', 'Balance']
        # move3_keys = [sheet.cell(9, col_index).value for col_index in range(sheet.ncols)]
        # move3_keys_standard = ['Дата', '№ документа', 'ИНН контрагента', 'Дебет', 'Кредит', '', 'Клиент', 'Назначение платежа']
        #
        # # trying to import
        # try:
        #     if len(set(move1_keys) & set(move1_keys_standard)) == len(move1_keys_standard):
        #         statements = self._parse_file_move1(data_file)
        #     elif len(set(move2_keys) & set(move2_keys_standard)) == len(move2_keys_standard):
        #         statements = self._parse_file_move2(data_file)
        #     elif len(set(move3_keys) & set(move3_keys_standard)) == len(move3_keys_standard):
        #         statements = self._parse_file_move3(data_file)
        #     else:  # else
        #         raise FileImportFormatError(_('Could not make sense of the given file.'))
        #     # Пост обработка для добавление валюты из журнала
        #     if 'currency_code' not in statements.keys():
        #         statements.update(dict(currency_code=self.currency_id.name))
        # except FileImportBaseError as exc:
        #     raise
        # except Exception as exc:
        #     _logger.error('{}'.format(exc))
        #     raise FileImportFormatError(_('Could not make sense of the given file.'))
        # return statements

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
    def _find_move_account_id(self, account_number):
        """ Get res.partner.move ID """
        move_account_id = None
        if account_number and len(account_number) > 4:
            move_account_ids = self.env['res.partner.move'].search(
                [('acc_number', '=', account_number)], limit=1)
            if move_account_ids:
                move_account_id = move_account_ids[0].id
        return move_account_id

    @api.model
    def _get_journal(self, currency_id, move_account_id):
        """ Find the journal """
        move_model = self.env['res.partner.move']
        # Find the journal from context, wizard or move account
        journal_id = self.env.context.get('journal_id') or self.journal_id.id
        currency = self.env['res.currency'].browse(currency_id)
        if move_account_id:
            move_account = move_model.browse(move_account_id)
            if journal_id:
                if (move_account.journal_id.id and
                        move_account.journal_id.id != journal_id):
                    raise UserError(
                        _('The account of this statement is linked to '
                          'another journal.'))
                if not move_account.journal_id.id:
                    move_model.write({'journal_id': journal_id})
            else:
                if move_account.journal_id.id:
                    journal_id = move_account.journal_id.id
        # If importing into an existing journal, its currency must be the same
        # as the move statement. When journal has no currency, currency must
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
                        'The currency of the move statement (%s) is not '
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
                        'The currency of the move statement (%s) is not '
                        'the same as the company currency (%s) !'
                    ) % (currency.name, company_currency.name))
        return journal_id

    @api.model
    @api.returns('res.partner.move')
    def _create_move_account(
            self, account_number, company_id=False, currency_id=False):
        """Automagically create move account, when not yet existing."""
        try:
            move_type = self.env.ref('base.move_normal')
            move_code = move_type.code
        except ValueError:
            move_code = 'move'
        vals_acc = {
            'acc_number': account_number,
            'state': move_code,
        }
        # Odoo users move accounts (which we import statement from) have
        # company_id and journal_id set while 'counterpart' move accounts
        # (from which statement transactions originate) don't.
        # Warning : if company_id is set, the method post_write of class
        # move will create a journal
        if company_id:
            vals = self.env['res.partner.move'].onchange_company_id(company_id)
            vals_acc.update(vals.get('value', {}))
            vals_acc['company_id'] = company_id

        # When the journal is created at same time of the move account, we need
        # to specify the currency to use for the account.account and
        # account.journal
        return self.env['res.partner.move'].with_context(
            default_currency_id=currency_id,
            default_currency=currency_id).create(vals_acc)

    @api.model
    def _complete_statement(self, stmt_vals, journal_id):
        """Дополняем statement с помощью предоставленной информации."""
        stmt_vals['journal_id'] = journal_id
        for line_vals in stmt_vals['transactions']:
            unique_import_id = line_vals.get('unique_import_id', False)
            # if unique_import_id:
            #     line_vals['unique_import_id'] = (
            #         (account_number and account_number + '-' or '') +
            #         unique_import_id
            #     )
            if not line_vals.get('move_account_id'):
                # Find the partner and his move account or create the move
                # account. The partner selected during the reconciliation
                # process will be linked to the move when the statement is
                # closed.
                partner_id = False
                partner_account_number = line_vals.get('account_number')
                if partner_account_number:
                    move_model = self.env['res.partner.move']
                    moves = move_model.search(
                        [('acc_number', '=', partner_account_number)], limit=1)
                    if moves:
                        move_account_id = moves[0].id
                        partner_id = moves[0].partner_id.id
                    else:
                        move_obj = self._create_move_account(
                            partner_account_number)
                        move_account_id = move_obj and move_obj.id or False
                line_vals['partner_id'] = partner_id
                # line_vals['move_account_id'] = move_account_id
        return stmt_vals

    @api.model
    def _create_move_statement(self, stmt_vals):
        """ Create move statement from imported values, filtering out
        already imported transactions, and return data used by the
        reconciliation widget
        """
        bs_model = self.env['account.move']
        bsl_model = self.env['account.move.line']
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
            move_id = bs_model.create(stmt_vals).id
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
                    'model': 'account.move.statement.line',
                    'ids': bsl_model.search(
                        [('unique_import_id', 'in', ignored_line_ids)]).ids}
            }]
        return move_id, notifications
