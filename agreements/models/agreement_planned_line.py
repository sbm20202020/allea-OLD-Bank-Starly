from odoo import models, fields, api


class AgreementPlannedLine(models.Model):
    """Agreement planned line model."""

    # - In a Model attribute order should be
    # === Private attributes (``_name``, ``_description``, ``_inherit``, ...)
    _name = 'agreement.planned.line'  # the model name
    _description = __doc__  # the model's informal name
    # === Default method and ``_default_get``
    # === Field declarations
    name = fields.Text(string='Description', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    product_qty = fields.Float(string='Quantity', digits='Product Unit of Measure', required=True)
    date_planned = fields.Datetime(string='Payment date', required=True, index=True)
    taxes_id = fields.Many2many('account.tax', string='Taxes', domain=['|', ('active', '=', False), ('active', '=', True)])
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure', domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    product_id = fields.Many2one('product.product', string='Product', change_default=True, required=True)
    price_unit = fields.Float(string='Unit Price', required=True, digits='Product Price')

    price_subtotal = fields.Monetary(compute='_compute_amount', string='Subtotal', store=True)
    price_total = fields.Monetary(compute='_compute_amount', string='Total', store=True)
    price_tax = fields.Float(compute='_compute_amount', string='Tax', store=True)

    agreement_id = fields.Many2one('agreement', string='Planned Agreement Reference', index=True, required=True,
                                   ondelete='cascade')
    company_id = fields.Many2one('res.company', related='agreement_id.company_id', string='Company', store=True,
                                 readonly=True)
    currency_id = fields.Many2one(related='agreement_id.currency_id', store=True, string='Currency', readonly=True)

    # === Compute, inverse and search methods in the same order as field declaration
    @api.depends('product_qty', 'price_unit', 'taxes_id')
    def _compute_amount(self):
        for line in self:
            vals = line._prepare_compute_all_values()
            taxes = line.taxes_id.compute_all(
                vals['price_unit'],
                vals['currency_id'],
                vals['product_qty'],
                vals['product'],
                vals['partner'])
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })
    # === Selection method (methods used to return computed values for selection fields)
    # === Constrains methods (``@api.constrains``) and onchange methods (``@api.onchange``)
    # === CRUD methods (ORM overrides)

    # === Action methods
    # === And finally, other business methods.
