from odoo import models, fields


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    company_id = fields.Many2one('res.company', 'Company', default=False, ondelete='cascade')
