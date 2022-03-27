# -*- coding: utf-8 -*-

from odoo import api, fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    moves_import_debug = fields.Boolean("Moves import with corrections", default=False, help="Move import with corrections on specific account")

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        get_param = self.env['ir.config_parameter'].sudo().get_param
        res.update(
            moves_import_debug=get_param('moves_import_debug', 'False').lower() == 'true',
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        set_param = self.env['ir.config_parameter'].sudo().set_param
        # we store the repr of the values, since the value of the parameter is a required string
        set_param('moves_import_debug', repr(self.moves_import_debug))
