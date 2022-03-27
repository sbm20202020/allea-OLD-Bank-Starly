from odoo import models, fields


class ResConfigSettings(models.TransientModel):

    _inherit = 'res.config.settings'

    interest_accrual_postings_type = fields.Selection(related='company_id.interest_accrual_postings_type',
                                                      readonly=False,
                                                      required=True)
