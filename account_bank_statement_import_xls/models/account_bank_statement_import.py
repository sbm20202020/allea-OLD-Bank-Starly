from odoo import fields, models


class AccountBankStatementImport(models.TransientModel):
    _inherit = 'account.bank.statement.import'

    date_filter_start = fields.Date(string='Date filter start', required=True, default=fields.Date.today)
    date_filter_end = fields.Date(string='Date filter end', required=True, default=fields.Date.today)
