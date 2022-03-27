from odoo import models, fields, api  # noqa: F401 #pylint: disable=W0611


class ResPartner(models.Model):

    _name = 'res.partner'  # the model name
    _inherit = 'res.partner'
    agreement_count = fields.Integer(compute='_compute_agreement_count', string='# Agreements')

    def _compute_agreement_count(self):
        Agreement = self.env['agreement']
        for agreement in self:
            agreement_id = agreement.id
            search_domain = ['|', '|',
                             ('partner_1_id', '=', agreement_id),
                             ('partner_2_id', '=', agreement_id),
                             ('partner_3_id', '=', agreement_id)]
            res = Agreement.search_count(search_domain)
            agreement.agreement_count = res or 0
