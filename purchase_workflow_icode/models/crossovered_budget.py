from odoo import models, fields


class CrossoveredBudget(models.Model):

    _inherit = 'crossovered.budget'

    company_id = fields.Many2one('res.company', 'Company', required=False)
