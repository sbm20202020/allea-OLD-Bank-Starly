import datetime

from odoo import models, fields, api


class Agreement(models.Model):
    """Agreement model"""

    _name = 'agreement'
    _inherit = ['mail.thread']

    agreement_type_id = fields.Many2one('agreement.type', string='Agreement type', required=True)
    amount = fields.Monetary(string='Agreement amount', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Agreement currency', required=True,
                                  default=lambda self: self.env.company.currency_id.id)
    comment = fields.Text('Comments')
    date_signed = fields.Datetime(string='Date signed')
    date_from = fields.Datetime(string='Effective date')
    date_end = fields.Datetime(string='End date')
    description = fields.Char(string='Short description', required=True)
    number = fields.Char(string='Agreement ID')
    name = fields.Char(string='Agreement name', required=True)
    partner_1_id = fields.Many2one('res.partner', string='Counterparty 1')
    partner_2_id = fields.Many2one('res.partner', string='Counterparty 2')
    partner_3_id = fields.Many2one('res.partner', string='Counterparty 3')
    prolongation = fields.Boolean(string='Autoprolongation')
    prolongation_period = fields.Selection([('monthly', 'Monthly'), ('quarterly', 'Quarterly'),
                                            ('yearly', 'Yearly'), ('other', 'Other')], string='Autoprolongation period')
    agreement_lines_ids = fields.One2many('agreement.planned.line', 'agreement_id', string='Planned Lines')
    responsible_ids = fields.Many2many('res.users', string='Responsible')
    agreement_actual_ids = fields.One2many('purchase.order.line', 'agreement_id', string='Actual purchase orders')
    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, compute='_amount_all',
                                     track_visibility='always')
    amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_amount_all')
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all')

    @api.depends('agreement_lines_ids.price_total')
    def _amount_all(self):
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.agreement_lines_ids:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
            order.update({
                'amount_untaxed': order.currency_id.round(amount_untaxed),
                'amount_tax': order.currency_id.round(amount_tax),
                'amount_total': amount_untaxed + amount_tax,
            })

    @api.model
    def create(self, vals):
        sequence = self.env['ir.sequence']
        date_signed = vals.get('date_signed', False)
        current_year = str(datetime.date.today().year)
        number = sequence.with_context(force_company=vals['company_id']).next_by_code('agreement')
        if not number:
            number = sequence.next_by_code('agreement.default')
        if date_signed:
            number = number.replace(current_year, date_signed[:4])
        vals['number'] = number
        result = super().create(vals)
        return result
