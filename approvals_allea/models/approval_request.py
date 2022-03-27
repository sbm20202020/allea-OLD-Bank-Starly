from odoo import fields, models, api, _
from odoo.exceptions import UserError


class ApprovalRequest(models.Model):
    _inherit = 'approval.request'

    create_document = fields.Selection(related="category_id.create_document")
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True,
                                 default=lambda self: self.env.company)
    approval_line_ids = fields.One2many('approval.request.line', 'approval_id', string='Approval Lines', copy=True)
    purchase_order_id = fields.Many2one('purchase.order', string='Related Purchase Order', ondelete='restrict')
    currency_id = fields.Many2one('res.currency', 'Currency', required=True,
                                  default=lambda self: self.env.company.currency_id.id)
    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, compute='_amount_all',
                                     tracking=True)
    amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_amount_all')
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all')
    notes = fields.Text('Terms and Conditions')
    date_planned = fields.Datetime(string='Receipt Date', index=True)
    partner_ref = fields.Char('Vendor Reference', copy=False,
                              help="Reference of the sales order or bid sent by the vendor. "
                                   "It's used to do the matching when you receive the "
                                   "products as this reference is usually written on the "
                                   "delivery order sent by your vendor.")
    state = fields.Selection([
        ('draft', 'RFQ'),
        ('sent', 'RFQ Sent'),
        ('to approve', 'To Approve'),
        ('purchase', 'Purchase Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled')
    ], string='Status', readonly=True, index=True, copy=False, default='draft', tracking=True)
    agreement_id = fields.Many2one('agreement', string='Purchase Agreement')
    vendor_date = fields.Date(string='Vendor Date')
    vendor_bank_account_id = fields.Many2one('res.partner.bank', string='Vendor Bank Account', required=True)
    wait_approver_ids = fields.Many2many('approval.approver', string="Waiting Approvers", compute='_compute_wait_approver_ids')

    @api.depends('approver_ids')
    def _compute_wait_approver_ids(self):
        for approval in self:
            approval.wait_approver_ids = approval.approver_ids.filtered(lambda approver: approver.status in ['new', 'pending'])

    @api.depends('approval_line_ids.price_total')
    def _amount_all(self):
        for approval in self:
            amount_untaxed = amount_tax = 0.0
            for line in approval.approval_line_ids:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
            approval.update({
                'amount_untaxed': approval.currency_id.round(amount_untaxed),
                'amount_tax': approval.currency_id.round(amount_tax),
                'amount_total': amount_untaxed + amount_tax,
            })

    @api.model
    def create(self, values):
        create_purchase_order = self.env['approval.category'].browse(values['category_id']).create_document
        approval_line_ids = values.get('approval_line_ids', False)
        if create_purchase_order == 'purchase_order' and not approval_line_ids:
            raise UserError(_("In Approval Request need to be at least one line."))
        return super().create(values)

    def action_approve(self, approver=None):
        super().action_approve(approver)
        if self.request_status == 'approved':
            create_purchase_order = self.category_id.create_document
            order_id = self.purchase_order_id
            if create_purchase_order == 'purchase_order' and not order_id:
                # create _method stored a new id in purchase_order_id
                company_id = self.company_id.id
                values = {
                    'partner_id': self.partner_id.id,
                    'company_id': company_id,
                    'vendor_date': self.vendor_date,
                    'agreement_id': self.agreement_id.id,
                    'date_planned': self.date_planned,
                    'currency_id': self.currency_id.id,
                    'state': 'purchase',
                    'approval_request_id': self.id,
                    'partner_ref': self.partner_ref,
                    'vendor_bank_account_id': self.vendor_bank_account_id.id,
                }
                arl_ids = self.approval_line_ids
                product_lines = []
                for arl in arl_ids:
                    product_values = {
                        'name': arl.name,
                        'product_id': arl.product_id.id,
                        'product_qty': arl.product_qty,
                        'product_uom': arl.product_uom.id,
                        'company_id': arl.company_id.id,
                        'price_unit': arl.price_unit,
                        'date_planned': arl.date_planned,
                        'display_type': arl.display_type,
                        'taxes_id': arl.taxes_id,
                        'account_analytic_id': arl.account_analytic_id.id,
                        'analytic_tag_ids': arl.analytic_tag_ids.ids,
                    }
                    product_lines.append((0, 0, product_values))
                if product_lines:
                    values['order_line'] = product_lines
                purchase_order__create_id = self.env['purchase.order'].with_context(force_company=company_id).create(
                    values)
                self.purchase_order_id = purchase_order__create_id
                # sync attachments
                attachments = self.env['ir.attachment'].search(
                    [('res_model', '=', 'approval.request'), ('res_id', '=', self.id)])
                for attachment in attachments:
                    values = {
                        'name': attachment.name,
                        'company_id': attachment.company_id.id,
                        'datas': attachment.datas,
                        'display_name': attachment.display_name,
                        'type': attachment.type,
                        'res_model': 'purchase.order',
                        'res_id': purchase_order__create_id.id
                    }
                    self.env['ir.attachment'].create(values)
                # sync messages
                domain = [('model', '=', 'approval.request'), ('res_id', '=', self.id),
                          ('message_type', '=', ['notification', 'comment'])]
                messages = self.env['mail.message'].search(domain)
                for message in messages:
                    values = {
                        'record_name': message.record_name,
                        'message_type': message.message_type,
                        'model': 'purchase.order',
                        'res_id': purchase_order__create_id.id,
                        'body': message.body,
                        'date': message.date,
                        'author_id': message.author_id.id
                    }
                    self.env['mail.message'].create(values)
