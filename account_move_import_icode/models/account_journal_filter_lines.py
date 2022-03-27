import logging
from odoo import api, models, fields
from odoo.tools.translate import _
from odoo.exceptions import Warning as UserError, RedirectWarning
_logger = logging.getLogger(__name__)


class AccountMoveStatementFilterLines(models.TransientModel):
    _name = 'account.move.statement.filter_lines'
    _description = 'Filter Move Statement'

    date_filter_start = fields.Date(string='Date filter start', required=True,
                                    default=lambda self: self._get_default_date_filter(True))
    date_filter_end = fields.Date(string='Date filter end', required=True,
                                  default=lambda self: self._get_default_date_filter(False))

    @api.model
    def _get_default_date_filter(self, date_start=True):
        context = dict(self._context or {})
        active_model = context.get('active_model', False)
        active_ids = context.get('active_ids', [])

        statements = self.env[active_model].browse(active_ids)
        dates = [fields.Datetime.from_string(s.date) for s in statements[-1].line_ids]
        if dates:
            date_filter_start = fields.Datetime.to_string(min(dates))
            date_filter_end = fields.Datetime.to_string(max(dates))
        else:
            date_filter_start = date_filter_end = fields.Datetime.now()
        return date_filter_start if date_start else date_filter_end

    def filter_lines(self):
        """фильтруем statement.lines"""
        context = dict(self._context or {})
        active_model = context.get('active_model', False)
        active_ids = context.get('active_ids', [])

        statements = self.env[active_model].browse(active_ids)

        return self._filter_lines(statements)

    def _filter_lines(self, statements):
        date_filter_start = fields.Datetime.from_string(self.date_filter_start)
        date_filter_end = fields.Datetime.from_string(self.date_filter_end)
        for statement in statements:
            if statement.state != 'open':  # New
                raise UserError(_("This command is only available for an statement with a 'New' status"))
            if date_filter_start > date_filter_end:
                raise UserError(_("End date must be greater than or equal to the start date"))
            aml_to_unbind = self.env['account.move.line']
            aml_to_cancel = self.env['account.move.line']

            line_ids = statement.line_ids.search(['&', ('statement_id', '=', statement.id),
                                                  '|', ('date', "<", self.date_filter_start),
                                                        ('date', ">", self.date_filter_end),
                                                ]).mapped('id')
            delete_list = [[2, obj, False] for obj in line_ids]

            statement.update({'line_ids': delete_list})
            # FIXME Хотя в логике оду баланс конечный в выписке и расчетный должен проверяться на расхождения, мы его пересчитываем автоматом - Гинько + Клиент <Ruzki 2018-08-30>
            statement.update({'balance_end': statement.balance_end_real})



        return {}
