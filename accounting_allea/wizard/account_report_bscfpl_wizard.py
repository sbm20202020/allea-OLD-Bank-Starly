import logging
import base64
from collections import defaultdict

from odoo import api, fields, models, _
from datetime import date, datetime, timedelta

_logger = logging.getLogger(__name__)


# class AccountReportBSCFPLWizard(models.TransientModel):
#     _name = "account.report.bscfpl_wizard"
#     file_name = fields.Char(default='BSCFPL.xlsx')
#     file_save = fields.Binary(string='xlsx File', readonly=True)
#
#     def _get_date_filter(self):
#         result = [
#             ('this_month', 'This Month'),
#             ('this_quarter', 'This Quarter'),
#             ('this_year', 'This Financial Year'),
#             ('last_month', 'Last Month'),
#             ('last_quarter', 'Last Quarter'),
#             ('last_year', 'Last Financial Year'),
#             # ('today', 'Today'),
#             # ('custom', 'custom'),
#         ]
#         # cmp = self.comparison_filter
#         # if cmp == 'no_comparison':
#         #     result = [
#         #         ('this_month', 'This Month'),
#         #         ('this_quarter', 'This Quarter'),
#         #         ('this_year', 'This Financial Year'),
#         #         ('last_month', 'Last Month'),
#         #         ('last_quarter', 'Last Quarter'),
#         #         ('last_year', 'Last Financial Year'),
#         #         ('today', 'Today'),
#         #         # ('custom', 'custom'),
#         #     ]
#         # else:
#         #     result = [
#         #         ('today', 'Today'),
#         #         ('last_month', 'End of Last Month'),
#         #         ('last_quarter', 'End of Last Quarter'),
#         #         ('last_year', 'End of Last Financial Year'),
#         #         # ('custom', 'custom'),
#         #     ]
#         return result
#
#     # options
#     comparison_filter = fields.Selection(string="Comparison",
#                                          selection=[
#                                              ('no_comparison', 'No comparison'),
#                                              ('same_last_year', 'Same Period Last Year'),
#                                              ('previous_period', 'Previous Period'),
#                                              # ('custom', 'Custom'),
#
#                                          ], default='no_comparison',
#                                          required=True, )
#     date_filter = fields.Selection(string="Date filter",
#                                    selection='_get_date_filter', default='today',
#                                    required=True, )
#     comparison_date_from = fields.Date(string='Date from', default=fields.Datetime.now)
#     comparison_date_to = fields.Date(string='Date to', default=fields.Datetime.now)
#     comparison_number_period = fields.Integer(string='Numbers of periods', default=0)
#
#     def button_export(self):
#         options = defaultdict(dict)
#         options['comparison']['filter'] = self.comparison_filter
#         options['date']['filter'] = self.date_filter or ''
#         if options['comparison']['filter'] == 'no_comparison':
#             pass
#         elif options['comparison']['filter'] == 'custom':
#             options['comparison']['date_from'] = self.comparison_date_from
#             options['comparison']['date_to'] = self.comparison_date_to
#         options['comparison']['number_period'] = self.comparison_number_period or None
#         options['comparison']['periods'] = []
#
#         options = dict(options)  # Во избежание
#         xlsx_data = self.env['account.report'].get_bscfpl_xlsx(options=options)
#         xlsx_data = base64.b64encode(xlsx_data)
#
#         self.write({
#             'file_save': xlsx_data,
#         })
#
#         return {
#             'type': 'ir.actions.act_window',
#             'res_model': self._name,
#             'view_type': 'form',
#             'view_mode': 'form',
#             'target': 'new',
#             'name': 'BS CF PL Report',
#             'res_id': self.id,
#             'context': dict(self._context),
#         }