from odoo import models, fields


class ApprovalApprover(models.Model):
    _inherit = 'approval.approver'

    name = fields.Char(related='user_id.name')
