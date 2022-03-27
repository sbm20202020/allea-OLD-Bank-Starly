from odoo import models, api, _
from odoo.exceptions import UserError


class DraftAccountMove(models.TransientModel):
    _name = "draft.account.move"
    _description = "Draft Account Move"

    def draft_move(self):
        context = dict(self._context or {})
        moves = self.env['account.move'].browse(context.get('active_ids'))
        move_to_draft = moves.filtered(lambda m: m.state == 'posted').sorted(lambda m: (m.date, m.ref or '', m.id))
        if not move_to_draft:
            raise UserError(_('There are no journal items in the post state to draft.'))
        move_to_draft.button_draft()
        return {'type': 'ir.actions.act_window_close'}
