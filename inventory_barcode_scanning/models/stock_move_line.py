from odoo import fields, models, api


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    barcode = fields.Char(string='Barcode')

    @api.onchange('barcode')
    def _onchange_barcode_scan(self):
        if self.barcode:
            lot_rec = self.env['stock.production.lot']
            lot = lot_rec.search([('name', 'like', self.barcode)])
            product = lot.product_id
            self.product_id = product.id
            self.lot_id = lot
