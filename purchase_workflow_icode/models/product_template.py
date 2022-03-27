from odoo import models, fields, api  # noqa: F401 #pylint: disable=W0611


class ProductTemplate(models.Model):
    """ProductTemplate"""

    _inherit = 'product.template'

    department_ids = fields.Many2many("hr.department", 'rel_product_template_hr_department', string='Department')

    @api.onchange('purchase_ok')
    def _onchange_purchase_ok(self):
        if not self.purchase_ok:
            self.department_ids = [(5, 0, 0)]
