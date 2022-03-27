from odoo import models, fields


class ProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    fields.Many2one('res.company', 'Company', stored=True, index=True)
