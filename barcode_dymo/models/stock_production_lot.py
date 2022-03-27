from odoo import fields, models


class StockProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    image = fields.Image(string="Image")
