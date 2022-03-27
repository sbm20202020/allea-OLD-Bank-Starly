from odoo import models, fields, api, _


class AccountMoveLine(models.Model):
    """AccountMoveLine"""

    _inherit = 'account.move.line'  # the model name

    # invoice_line_id = fields.Many2one('account.move.line', 'Invoice Line')
    # is_invoice_line_id_matched = fields.Boolean(default=False)
    # invoice_tax_line_id = fields.Many2one('account.move.line', 'Tax Line')
    # reversal_of_id = fields.Integer(related='move_id.reversal_of_id', string="Is reversal of")
    # reversed_by_id = fields.Integer(related='move_id.reversed_by_id', string="Was reversed by")
    # last_odd_reverse = fields.Boolean(related='move_id.last_odd_reverse', string="Is odd reverse")
    # editable_tags = fields.Boolean(compute="_compute_editable_tags")

    # def _compute_editable_tags(self):
    #     can_edit = self.env.user.has_group('account_icode.group_change_move_a_tags')
    #     for line in self:
    #         line.editable_tags = can_edit



    # analytic_account_id
    # @api.depends('analytic_account_id')
    # def onchange_analytic_account_id(self):
    #     if self.move_id.state == 'posted':
    #         self.move_id.post()


    # @api.constrains('analytic_tag_ids', 'analytic_account_id')
    # def _constrains_analytic_tag_ids(self):
    #     for move_line_id in self:
    #         invoice_line_id = move_line_id.invoice_line_id
    #         expense_id = move_line_id.expense_id
    #         invoice_tax_line_id = move_line_id.invoice_tax_line_id
    #         if invoice_line_id:
    #             invoice_line_id.analytic_tag_ids = move_line_id.analytic_tag_ids
    #             invoice_line_id.account_analytic_id = move_line_id.analytic_account_id
    #         if expense_id:
    #             expense_id.analytic_tag_ids = move_line_id.analytic_tag_ids
    #             expense_id.account_analytic_id = move_line_id.analytic_account_id
    #         if invoice_tax_line_id:
    #             invoice_tax_line_id.analytic_tag_ids = move_line_id.analytic_tag_ids
    #             invoice_tax_line_id.account_analytic_id = move_line_id.analytic_account_id
