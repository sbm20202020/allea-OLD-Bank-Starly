from odoo import models, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    # @api.model
    # def default_get(self, default_fields):
    #     # OVERRIDE
    #     values = super().default_get(default_fields)
    #     invoice_date = values.get('invoice_date')
    #     invoice_id = values.get('purchase_id')
    #     if invoice_date and invoice_id:
    #         date_approve = self.env['purchase.order'].browse(invoice_id).date_approve
    #         values['invoice_date'] = date_approve
    #     return values

    @api.model_create_multi
    def create(self, vals_list):
        result = super().create(vals_list)
        account_move_id = result.id
        purchase_order_id = self.env['purchase.order'].search([('invoice_ids', '=', account_move_id)])
        if purchase_order_id:
            domain = [('res_model', '=', 'purchase.order'), ('res_id', '=', purchase_order_id.id)]
            attachments_ids = self.env['ir.attachment'].search(domain)
            for attachment in attachments_ids:
                values = {
                    'name': attachment.name,
                    'company_id': attachment.company_id.id,
                    'datas': attachment.datas,
                    'display_name': attachment.display_name,
                    'type': attachment.type,
                    'res_model': 'account.move',
                    'res_id': account_move_id,
                }
                self.env['ir.attachment'].create(values)
            domain = [('model', '=', 'purchase.order'), ('res_id', '=', purchase_order_id.id)]
            message_ids = self.env['mail.message'].search(domain)
            for message in message_ids:
                values = {
                    'message_type': message.message_type,
                    'subject': message.subject,
                    'date': message.date,
                    'model': 'account.move',
                    'res_id': account_move_id,
                    'subtype_id': message.subtype_id.id,
                    'author_id': message.author_id.id,
                    'body': message.body,
                }
                self.env['mail.message'].create(values)
        return result
