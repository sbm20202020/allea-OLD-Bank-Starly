from odoo import models, fields, api


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    display_name = fields.Char(compute='_compute_display_name', store=True, index=True)

    @api.depends('bank_name', 'acc_number')
    def _compute_display_name(self):
        for bank in self:
            if bank.bank_name and bank.acc_number:
                names = [bank.bank_name, bank.acc_number]
                bank.display_name = '-'.join(names)

    def name_get(self):
        result = []
        for bank in self:
            if bank.display_name:
                result.append((bank.id, bank.display_name))
            else:
                result.append((bank.id, bank.acc_number))
        return result
