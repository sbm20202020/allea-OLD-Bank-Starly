from odoo import models, fields

TAG_CATEGORY = [('cat1', 'Income'),
                ('cat2', 'Expenses'),
                ('cat3', 'Services received or Goods purchased'),
                ('cat4', 'Local Expenses')]


class AccountTaxGroup(models.Model):
    _inherit = 'account.tax.group'

    vat_report_analytic_tag_category = fields.Selection(TAG_CATEGORY, string='TAX Tag Category', default='cat1',
                                                        required=True)
