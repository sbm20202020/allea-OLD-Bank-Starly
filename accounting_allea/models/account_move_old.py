import time
from collections import OrderedDict
from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.exceptions import RedirectWarning, UserError, ValidationError
from odoo.tools.misc import formatLang
from odoo.tools import float_is_zero, float_compare
from odoo.tools.safe_eval import safe_eval
from odoo.addons import decimal_precision as dp
from lxml import etree


class AccountMove(models.Model):
    _inherit = "account.move"

    line_ids = fields.One2many('account.move.line', 'move_id', string='Journal Items',
        states={'posted': [('readonly', False)]}, copy=True)

    reversal_of_id = fields.Integer(string="Is reversal of",  # instance of reversing
                                    required=True, copy=False, default=0)
    reversed_by_id = fields.Integer(string="Was reversed by",
                                    required=True, copy=False, default=0)

    last_odd_reverse = fields.Boolean(string="Is odd reverse", default=False)

    #@api.model
    def get_reversal_chain(self):
        ch_list = []
        move = self
        if move.reversal_of_id:
            ch_list.append(move.id)
            while move.reversal_of_id:
                ch_list.append(move.reversal_of_id)
                move = move.browse(move.reversal_of_id)
        return ch_list

    def _reverse_move(self, date=None, journal_id=None):
        
        if self.reversed_by_id:
            raise ValidationError('This entry is already reversed by another reversal operation {}. Please, check it.'.format(self.browse(self.reversed_by_id).ref))
        reversed_move = super()._reverse_move(date, journal_id)
        reversed_move.write({'reversal_of_id': self.id})
        self.write({'reversed_by_id': reversed_move.id})
        ch_list = reversed_move.get_reversal_chain()
        self.update({'last_odd_reverse': False})
        if len(ch_list) % 2:
            reversed_move.update({'last_odd_reverse': True})
        else:
            reversed_move.update({'last_odd_reverse': False})
            
        # for acm_line in reversed_move.line_ids.with_context(check_move_validity=False):
        #     acm_line.write({
        #         'reversal_of_id': self.id,
        #         'last_odd_reverse': last_odd_reverse,
        #     })
        # for acm_line in self.line_ids.with_context(check_move_validity=False):
        #     acm_line.write({
        #         'reversed_by_id': reversed_move.id,
        #         'last_odd_reverse': False,
        #     })

        return reversed_move


