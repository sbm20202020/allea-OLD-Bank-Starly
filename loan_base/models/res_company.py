from odoo import models, fields


class ResCompany(models.Model):
    """Company"""

    _inherit = 'res.company'

    create_la_when_lending_to_this_company = fields.Boolean('Create Loan Agreements when lending to this company')
    create_la_when_borrow_from_this_company = fields.Boolean('Create Loan Agreements when borrow from this company')
    interest_accrual_postings_type = fields.Selection([('manual', 'Manual'), ('auto', 'Automatic')],
                                                      string="Interest Accrual Postings Type",
                                                      default='manual')
    is_lender = fields.Boolean('Lender', related='partner_id.is_lender', default=False)
    is_borrower = fields.Boolean('Borrower', related='partner_id.is_borrower', default=False)
