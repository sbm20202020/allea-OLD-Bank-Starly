from odoo import api, models, fields
from odoo.exceptions import UserError
import base64
import string

ALLOWED_CHARS = string.ascii_uppercase + string.digits


class ExportEurobankWizard(models.TransientModel):
    _name = 'export.eurobank.wizard'

    data = fields.Binary('File', readonly=True)
    filename = fields.Char('File Name', readonly=True)

    def cancel_email(self):
        data = self.generate_statement()
        data_bytes = base64.b64encode(data.encode('UTF-8'))
        date_today = fields.Date.today()
        name = 'eurobank_statement-%s' % date_today
        extension = 'txt'
        filename = '%s.%s' % (name, extension)
        self.write({'filename': ('%s' % filename), 'data': data_bytes})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'export.eurobank.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def generate_statement(self):
        data = {}
        active_ids = self._context.get('active_ids')
        euro_countries_ids = self.env['res.country.group'].browse(1).country_ids
        purchase_order_ids = self.env['purchase.order'].browse(active_ids)
        result = False
        for purchase_order in purchase_order_ids:
            information = []
            partner_id_name = purchase_order.partner_id.name
            purchase_order_name = purchase_order.name
            vendor_bank_account = purchase_order.vendor_bank_account_id
            company_bank_account_id = purchase_order.company_bank_account_id
            if not vendor_bank_account:
                raise UserError("%s don't have vendor bank account" % purchase_order_name)
            if not company_bank_account_id:
                raise UserError("%s don't have company bank account" % purchase_order_name)
            key = (vendor_bank_account.id, company_bank_account_id.id)
            if key in data:
                pass
            else:
                from_account = company_bank_account_id.bank_acc_number
                information.append(from_account)
                beneficiary_name = partner_id_name
                information.append(beneficiary_name[:35])
                swift_code = vendor_bank_account.bank_bic
                if not swift_code:
                    raise UserError("%s don't have BIC/SWIFT number" % vendor_bank_account.bank_id.name)
                swift_code = swift_code
                information.append(swift_code)
                bank_name = vendor_bank_account.bank_id.name[:35]
                information.append(bank_name)
                beneficiary_account = vendor_bank_account.sanitized_acc_number
                information.append(beneficiary_account)
                amount = purchase_order.amount_total
                information.append(amount)
                currency = purchase_order.currency_id.name
                information.append(currency)
                if vendor_bank_account.bank_id.country in euro_countries_ids:
                    correspondent_charges = 'SHA'
                else:
                    correspondent_charges = 'OUR'
                information.append(correspondent_charges)
                beneficiary_address = ' '
                information.append(beneficiary_address)
                bank_address = ' '
                information.append(bank_address)
                branch_name = ' '
                information.append(branch_name)
                order_partner_ref = purchase_order.partner_ref
                if order_partner_ref:
                    detail_of_payment_1 = order_partner_ref
                else:
                    detail_of_payment_1 = ' '
                information.append(detail_of_payment_1)
                order_vendor_date = purchase_order.vendor_date
                if order_vendor_date:
                    detail_of_payment_2 = order_vendor_date
                else:
                    detail_of_payment_2 = ' '
                information.append(detail_of_payment_2)
                detail_of_payment_3 = ' '
                information.append(detail_of_payment_3)
                detail_of_payment_4 = ' '
                information.append(detail_of_payment_4)
                if vendor_bank_account.bank_id.country in euro_countries_ids:
                    payment_method = '2'  # SEPA
                else:
                    payment_method = '1'  # SWIFT
                information.append(payment_method)
                if vendor_bank_account.bank_id.country in euro_countries_ids:
                    value_date = '1'
                else:
                    value_date = '2'
                information.append(value_date)
                information.append('')
                information.append('')
                data[key] = information
        result = '\n'.join(data.values())
        return result
