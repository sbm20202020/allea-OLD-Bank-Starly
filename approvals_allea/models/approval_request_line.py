from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo import fields, models, api, _
from odoo.tools.misc import get_lang


class ApprovalRequestLine(models.Model):
    _name = 'approval.request.line'
    _description = 'Approval Request Line'
    _order = 'approval_id, sequence, id'

    name = fields.Text(string='Description', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    product_qty = fields.Float(string='Quantity', digits='Product Unit of Measure', required=True)
    product_uom_qty = fields.Float(string='Total Quantity', compute='_compute_product_uom_qty', store=True)
    date_planned = fields.Datetime(string='Scheduled Date', index=True)
    taxes_id = fields.Many2many('account.tax', string='Taxes',
                                domain=['|', ('active', '=', False), ('active', '=', True)])
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure',
                                  domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    product_id = fields.Many2one('product.product', string='Product', domain=[('purchase_ok', '=', True)],
                                 change_default=True)
    product_type = fields.Selection(related='product_id.type', readonly=True)
    price_unit = fields.Float(string='Unit Price', required=True, digits='Product Price')

    price_subtotal = fields.Monetary(compute='_compute_amount', string='Subtotal', store=True)
    price_total = fields.Monetary(compute='_compute_amount', string='Total', store=True)
    price_tax = fields.Float(compute='_compute_amount', string='Tax', store=True)

    approval_id = fields.Many2one('approval.request', string='Approval Reference', index=True, required=True,
                                  ondelete='cascade')
    account_analytic_id = fields.Many2one('account.analytic.account', string='Analytic Account', required=True)
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags')
    company_id = fields.Many2one('res.company', related='approval_id.company_id', string='Company', store=True,
                                 readonly=True)
    state = fields.Selection(related='approval_id.request_status', store=True, readonly=False)

    qty_received_method = fields.Selection([('manual', 'Manual')], string="Received Qty Method",
                                           compute='_compute_qty_received_method', store=True,
                                           help="According to product configuration, the received quantity can be "
                                                "automatically computed by mechanism :\n "
                                                "  - Manual: the quantity is set manually on the line\n"
                                                "  - Stock Moves: the quantity comes from confirmed pickings\n")
    qty_received = fields.Float("Received Qty", compute='_compute_qty_received', inverse='_inverse_qty_received',
                                compute_sudo=True, store=True, digits='Product Unit of Measure')
    qty_received_manual = fields.Float("Manual Received Qty", digits='Product Unit of Measure', copy=False)

    partner_id = fields.Many2one('res.partner', related='approval_id.partner_id', string='Partner', readonly=True,
                                 store=True)
    currency_id = fields.Many2one(related='approval_id.currency_id', store=True, string='Currency', readonly=True)

    display_type = fields.Selection([
        ('line_section', "Section"),
        ('line_note', "Note")], default=False, help="Technical field for UX purpose.")

    _sql_constraints = [
        ('accountable_required_fields',
         "CHECK(display_type IS NOT NULL OR (product_id IS NOT NULL AND product_uom IS NOT NULL AND date_planned IS NOT NULL))",
         "Missing required fields on accountable approvals order line."),
        ('non_accountable_null_fields',
         "CHECK(display_type IS NULL OR (product_id IS NULL AND price_unit = 0 AND product_uom_qty = 0 AND product_uom IS NULL AND date_planned is NULL))",
         "Forbidden values on non-accountable approvals order line"),
    ]

    barcode = fields.Char(string='Barcode')

    @api.onchange('barcode')
    def barcode_scanning(self):
        company_id = self.company_id.id
        barcode = self.barcode
        if not company_id:
            raise Warning('Please set company before add products')
        if barcode:
            domain = [('name', 'like', barcode), ('company_id', '=', company_id)]
            lot_id = self.env['stock.production.lot'].search(domain)
            if lot_id:
                product_id = lot_id.product_id.id
                self.product_id = product_id

    @api.onchange('qty_received')
    def _inverse_qty_received(self):
        """ When writing on qty_received, if the value should be modified manually (`qty_received_method` = 'manual'
        only), then we put the value in `qty_received_manual`. Otherwise, `qty_received_manual` should be False since
        the received qty is automatically compute by other mechanism.
        """
        for line in self:
            if line.qty_received_method == 'manual':
                line.qty_received_manual = line.qty_received
            else:
                line.qty_received_manual = 0.0

    @api.depends('qty_received_method', 'qty_received_manual')
    def _compute_qty_received(self):
        for line in self:
            if line.qty_received_method == 'manual':
                line.qty_received = line.qty_received_manual or 0.0
            else:
                line.qty_received = 0.0

    @api.depends('product_id')
    def _compute_qty_received_method(self):
        for line in self:
            if line.product_id and line.product_id.type in ['consu', 'service']:
                line.qty_received_method = 'manual'
            else:
                line.qty_received_method = False

    @api.depends('product_uom', 'product_qty', 'product_id.uom_id')
    def _compute_product_uom_qty(self):
        for line in self:
            if line.product_id and line.product_id.uom_id != line.product_uom:
                line.product_uom_qty = line.product_uom._compute_quantity(line.product_qty, line.product_id.uom_id)
            else:
                line.product_uom_qty = line.product_qty

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

    def _prepare_compute_all_values(self):
        # Hook method to returns the different argument values for the
        # compute_all method, due to the fact that discounts mechanism
        # is not implemented yet on the purchase orders.
        # This method should disappear as soon as this feature is
        # also introduced like in the sales module.
        self.ensure_one()
        return {
            'price_unit': self.price_unit,
            'currency_id': self.approval_id.currency_id,
            'product_qty': self.product_qty,
            'product': self.product_id,
            'partner': self.approval_id.partner_id,
        }

    @api.model
    def create(self, values):
        if values.get('display_type', self.default_get(['display_type'])['display_type']):
            values.update(product_id=False, price_unit=0, product_uom_qty=0, product_uom=False, date_planned=False)

        order_id = values.get('order_id')
        if 'date_planned' not in values:
            order = self.env['purchase.order'].browse(order_id)
            if order.date_planned:
                values['date_planned'] = order.date_planned
        line = super().create(values)
        if line.approval_id.state == 'pending':
            msg = _("Extra line with %s ") % (line.product_id.display_name,)
            line.approval_id.message_post(body=msg)
        return line

    @api.onchange('product_id')
    def onchange_product_id(self):
        if not self.product_id:
            return

        self.date_planned = datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        self.price_unit = self.product_qty = 0.0

        self._product_id_change()

    def _product_id_change(self):
        if not self.product_id:
            return

        self.product_uom = self.product_id.uom_po_id or self.product_id.uom_id
        product_lang = self.product_id.with_context(
            lang=get_lang(self.env, self.partner_id.lang).code,
            partner_id=self.partner_id.id,
            company_id=self.company_id.id,
        )
        self.name = self._get_product_purchase_description(product_lang)

        self._compute_tax_id()

    def _get_product_purchase_description(self, product_lang):
        self.ensure_one()
        name = product_lang.display_name
        if product_lang.description_purchase:
            name += '\n' + product_lang.description_purchase

        return name

    def _compute_tax_id(self):
        for line in self:
            fpos = line.approval_id.partner_id.with_context(
                force_company=line.company_id.id).property_account_position_id
            # If company_id is set, always filter taxes by the company
            taxes = line.product_id.supplier_taxes_id.filtered(
                lambda r: not line.company_id or r.company_id == line.company_id)
            line.taxes_id = fpos.map_tax(taxes, line.product_id, line.approval_id.partner_id) if fpos else taxes
