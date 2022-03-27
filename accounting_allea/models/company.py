from odoo import models
from dateutil.relativedelta import relativedelta


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _parse_ecb_data(self, available_currencies):
        ''' This method is used to update the currencies by using ECB service provider.
            Rates are given against EURO
        '''
        result = super()._parse_ecb_data(available_currencies)
        for key, value in result.items():
            date = value[1] + relativedelta(days=-1)
            result[key] = (value[0], date)
        return result
