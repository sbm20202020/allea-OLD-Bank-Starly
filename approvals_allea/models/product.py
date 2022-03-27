from odoo import fields, models


# class ProductTemplate(models.Model):
#     _inherit = 'product.template'
#
#     user_ids = fields.Many2many('res.users', string='Allowed Users')
#
#
# class ProductCategory(models.Model):
#     _inherit = "product.category"
#
#     user_ids = fields.Many2many('res.users', string='Allowed Users')


class ProductTemplate(models.Model):
    """Product template"""
    _inherit = 'product.template'

    user_ids = fields.Many2many('res.users', string='Allowed Users')
