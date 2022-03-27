# -*- coding: utf-8 -*-
# Standard libs
import datetime
from lxml import etree, objectify
from dateutil.relativedelta import relativedelta
import re
import logging

import requests
from datetime import datetime

# Third party libs
from odoo import models, fields, api, _
from odoo.addons.web.controllers.main import xml2json_from_elementtree

# Module variables init
_logger = logging.getLogger(__name__)
"""

Заготовка под обновление курсов валют при СОЗДАНИИ новой компании с начала 2017 года по текущий день.
тут есть по текущей дате только, но ЕЦБ отдаеют прекрасный csv файл с курсами за все время. если будем делать, 
будем работать с ним.


class ResCompany(models.Model):
    _inherit = 'res.company'


    def update_currency_rates_from_2017(self):
        ''' Update currencies from start of the year. '''
        res = True
        all_good = True
        for company in self:
            if company.currency_provider == 'ecb':
                res = company._update_currency_ecb_from_2017()
            if not res:
                all_good = False
                _logger.warning(_('Unable to connect to the online exchange rate platform %s. The web service may be temporary down.') % company.currency_provider)
            elif company.currency_provider:
                company.last_currency_sync_date = fields.Date.today()

        return all_good



    def _update_currency_ecb_from_2017(self):
        ''' This method is used to update the currencies by using ECB service provider.
            Rates are given against EURO
        '''
        Currency = self.env['res.currency']
        CurrencyRate = self.env['res.currency.rate']

        currencies = Currency.search([])
        currencies = [x.name for x in currencies]
        request_url = "http://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
        try:
            parse_url = requests.request('GET', request_url)
        except:
            #connection error, the request wasn't successful
            return False
        xmlstr = etree.fromstring(parse_url.content)
        data = xml2json_from_elementtree(xmlstr)
        node = data['children'][2]['children'][0]
        currency_node = [(x['attrs']['currency'], x['attrs']['rate']) for x in node['children'] if x['attrs']['currency'] in currencies]
        for company in self:
            base_currency_rate = 1
            if company.currency_id.name != 'EUR':
                #find today's rate for the base currency
                base_currency = company.currency_id.name
                base_currency_rates = [(x['attrs']['currency'], x['attrs']['rate']) for x in node['children'] if x['attrs']['currency'] == base_currency]
                base_currency_rate = len(base_currency_rates) and base_currency_rates[0][1] or 1
                currency_node += [('EUR', '1.0000')]

            for currency_code, rate in currency_node:
                rate = float(rate) / float(base_currency_rate)
                currency = Currency.search([('name', '=', currency_code)], limit=1)
                if currency:
                    c_r_exists = CurrencyRate.search([{'currency_id': currency.id, 'rate': rate, 'name': fields.Date.today(), 'company_id': company.id}], limit=1)
                    CurrencyRate.create({'currency_id': currency.id, 'rate': rate, 'name': fields.Date.today(), 'company_id': company.id})
        return True
"""