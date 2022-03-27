from odoo import models, fields, api


class AccountInvoice(models.Model):
    """AccountInvoice"""

    _inherit = 'account.move'

    @api.model
    def default_get(self, default_fields):
        res = super().default_get(default_fields)
        purchase_id = res.get('purchase_id', False)
        if purchase_id:
            def _filter(attribute):
                return attribute.body != '' or attribute.attachment_ids

            def _sort(attribute):
                return attribute.date

            message_ids = self.env['purchase.order'].browse(purchase_id).message_ids.filtered(_filter).sorted(key=_sort)
            data_message = []
            for message in message_ids:
                data = message.copy_data()
                data[0]['model'] = 'account.move'
                data[0].pop('res_id')
                data_message.append((0, 0, data[0]))
            res['message_ids'] = data_message
        return res

    invoice_line_ids = fields.One2many('account.move.line', 'move_id', string='Invoice Lines', readonly=False, copy=True)
    tax_line_ids = fields.One2many('account.move.line', 'move_id', string='Tax Lines', readonly=False, copy=True)

    def _prepare_invoice_line_from_po_line(self, line):
        data = super(AccountInvoice, self)._prepare_invoice_line_from_po_line(line)
        invoice_line = self.env['account.move.line']
        account = invoice_line.get_invoice_line_account('in_invoice',
                                                        line.with_context(force_company=line.company_id.id).product_id,
                                                        line.order_id.fiscal_position_id, line.company_id)
        if account:
            data['account_id'] = account.id
        return data

    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        if self.journal_id:
            self.currency_id = self.journal_id.currency_id.id or self.journal_id.company_id.currency_id.id
        currency_id = self.env.context.get('default_currency_id')
        if currency_id:
            self.currency_id = currency_id

    def _create_analytic_line(self, vals, change_field, search_field):
        line_ids = vals.get(change_field)
        if line_ids:
            for line in line_ids:
                line_val = line[2]
                line_id = line[1]
                if line_val:
                    write_expr = {}
                    analytic_id = line_val.get('account_analytic_id')
                    analytic_tags = line_val.get('analytic_tag_ids')
                    if analytic_id is not None:
                        write_expr['analytic_account_id'] = analytic_id
                    if analytic_tags is not None:
                        write_expr['analytic_tag_ids'] = analytic_tags
                    if write_expr:
                        aml = self.env['account.move.line'].search([(search_field, '=', line_id)])
                        if aml:
                            aml.write(write_expr)
                            aml.create_analytic_lines()

    def write(self, values):
        result = True
        for invoice in self:
            if invoice.state != 'draft':
                tax_line_ids = values.get('tax_line_ids')
                if tax_line_ids:
                    analytic_accounts_ids = []
                    tax_ids = []
                    write_expr = []
                    for tax_line in tax_line_ids:
                        if tax_line[0] == 0:
                            analytic_accounts_ids.append(tax_line[2].get('account_analytic_id'))
                        elif tax_line[0] == 2:
                            tax_ids.append(tax_line[1])
                        elif tax_line[0] == 1:
                            write_expr.append(tax_line)
                    if analytic_accounts_ids or tax_ids:
                        for step in range(len(analytic_accounts_ids)):
                            write_expr.append([1, tax_ids[step], {'account_analytic_id': analytic_accounts_ids[step]}])
                    values['tax_line_ids'] = write_expr
            result = super().write(values)
            invoice._create_analytic_line(values, 'invoice_line_ids', 'invoice_line_id')
            invoice._create_analytic_line(values, 'tax_line_ids', 'invoice_tax_line_id')
        return result
