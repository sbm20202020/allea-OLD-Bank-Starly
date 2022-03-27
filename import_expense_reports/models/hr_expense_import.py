"""
Module is designed taking into account the odoo guidelines:
  `https://www.odoo.com/documentation/12.0/reference/guidelines.html`
"""
# === Standard library imports ===
import datetime
import logging
import base64
from io import BytesIO

# === Init logger ================
_logger = logging.getLogger(__name__)

# === Third party imports ========
import xlrd

# === Imports of odoo ============
from odoo import models, fields, api, _
from odoo.exceptions import UserError

# === Imports from odoo addons ===
# from odoo.addons.website.models.website import slug

# === Local application imports ==
# from ..exceptions import BaseModuleNameError

# === CONSTANTS ==================
EXPENSES_KEY_DICT = {'name': 2,
                     'currency_id': 6,
                     'unit_amount': 9,
                     'date': 11,
                     }

TRAVEL_KEY_DICT = {'date': 2,
                   'name': 4,
                   'currency_id': 6,
                   'unit_amount': 7,
                   }
HEADER_ROW_IDX = 11

# === Module init variables ======
# myvar = 'test'


class HrExpenseImport(models.TransientModel):
    """HrExpenseImport"""
    # - In a Model attribute order should be
    # === Private attributes (``_name``, ``_description``, ``_inherit``, ...)
    _name = 'hr.expense.import'
    _description = 'Import Expense/Travel Report'
    # === Default method and ``_default_get``
    # === Field declarations
    # analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags')
    type_file = fields.Selection([('expense', 'Expense Report'), ('travel', 'Travel Report')], required=True,
                                 default='expense')
    report_file = fields.Binary(string='Report .xlsx file', required=True,
                                help='Get your expense or travel report in xlsx format and select them here.')
    filename = fields.Char()

    # === Compute, inverse and search methods in the same order as field declaration
    # === Selection method (methods used to return computed values for selection fields)
    # === Constrains methods (``@api.constrains``) and onchange methods (``@api.onchange``)
    # === CRUD methods (ORM overrides)
    # === Action methods

    def import_report(self):
        self.ensure_one()
        # Reading XLSX file
        data_file = base64.b64decode(self.report_file)
        fp = BytesIO(data_file)
        book = xlrd.open_workbook(file_contents=fp.read())
        sheet = book.sheet_by_index(0)
        # Header Check XLSX
        keys = [sheet.cell(HEADER_ROW_IDX, col_index).value for col_index in range(sheet.ncols)]
        travel_keys_standard = \
            ['', 'Nr.', 'Date', 'Description', 'Name', '', 'Currency', 'Amount', 'FX rate', '', 'Cash', '']
        expense_keys_standard = ['', 'Nr.', '', 'Name', '', '', 'Currency', 'Sum', 'FX', '', 'Cash', 'Date']
        if self.type_file == 'expense' and keys == expense_keys_standard:
            date_report = sheet.cell_value(5, 3)
            date_report = datetime.datetime(*xlrd.xldate_as_tuple(date_report, book.datemode))
            name = 'Expense Report {0}'.format(date_report.date())
            data_dict = self.read_report(book, EXPENSES_KEY_DICT)
        elif self.type_file == 'travel' and travel_keys_standard:
            date_report = sheet.cell_value(5, 4)
            date_report = datetime.datetime(*xlrd.xldate_as_tuple(date_report, book.datemode))
            name = 'Travel Report {0}'.format(date_report.date())
            data_dict = self.read_report(book, TRAVEL_KEY_DICT)
        else:
            raise UserError(_('Please, check Type File.'))
        data_dict['name'] = name
        sheet_id = self.env['hr.expense.sheet'].create(data_dict).id
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'res_id': sheet_id,
            'res_model': 'hr.expense.sheet',
            'type': 'ir.actions.act_window',
        }

    def read_report(self, book, key_dict):
        """Read xlsx file to dict

        :param book:
        :param key_dict:
        :return:
        :rtype: dict
        """
        data_dict = dict()
        sheet = book.sheet_by_index(0)

        name_person = sheet.cell_value(8, 3)
        employee_id = self.env['hr.employee'].search([('name', '=', name_person)]).id
        if employee_id:
            data_dict['employee_id'] = employee_id
        else:
            raise UserError(_('Please, choose right employee in report.'))

        expense_lines = list()
        ResCurrency = self.env['res.currency']
        for row_number in range(HEADER_ROW_IDX + 2, sheet.nrows):
            row = sheet.row(row_number)
            if len(row) > 5 and sheet.cell_value(row_number, 2):
                r = {k: sheet.cell_value(row_number, v) for k, v in key_dict.items()}
                r['date'] = datetime.datetime(*xlrd.xldate_as_tuple(r['date'], book.datemode))

                currency_id = ResCurrency.search([('name', '=', r['currency_id'])])
                if currency_id:
                    r['currency_id'] = currency_id.id
                else:
                    r['currency_id'] = self.env.ref('base.EUR').id

                r['employee_id'] = employee_id
                r['product_id'] = self.env.ref('hr_expense.product_product_fixed_cost').id
                expense_lines.append((0, 0, r))
        data_dict['expense_line_ids'] = expense_lines
        return data_dict
    # === And finally, other business methods.
