import datetime
import logging
import urllib.parse
import uuid
from odoo import models, fields, api
from odoo.exceptions import AccessDenied

_logger = logging.getLogger(__name__)


class LoginUrlResUsers(models.Model):
    _name = 'res.users'
    _inherit = 'res.users'

    login_for_token = fields.Char(copy=False)
    login_for_link = fields.Char()
    login_for_token_birth_time = fields.Datetime()

    def set_login_url(self):
        # Set the token
        self.login_for_token = uuid.uuid4().hex
        _logger.info("User <%s> created a login token: <%s> to log in as user <%s>",
                     self.env.user.name,
                     self.login_for_token,
                     self.name
                     )
        self.login_for_token_birth_time = datetime.datetime.now()
        _logger.info("Token <%s> related to user <%s> will expire in 60 seconds.",
                     self.login_for_token,
                     self.name,
                     )

        # Set arguments for url
        url_params = {
            'db': self._cr.dbname,
            'user_name': self.name,
            'res_id': self.id,
            'token': self.login_for_token,
            'admin_name': self.env.user.name,
        }

        # Find base url
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

        # Set login link
        self.login_for_link = '{}/custom_login?{}'.format(base_url, urllib.parse.urlencode(url_params))

        return {
            "type": "ir.actions.do_nothing",
        }

    @api.model
    def check_credentials(self, password):
        try:
            return super(LoginUrlResUsers, self).check_credentials(password)
        except AccessDenied:
            res = self.sudo().search([('id', '=', self.env.uid), ('login_for_token', '=', password)])
            if not res:
                raise

    def modal_field_for_login_link(self):
        LoginUrlResUsers.set_login_url(self)
        view_id = self.env.ref('icode_debug_login_for.modal_view_for_login_management').id
        return {
            'name': 'Login management',
            'view_type': 'form',
            'view_mode': 'tree',
            'views': [(view_id, 'form')],
            'res_model': 'res.users',
            'view_id': view_id,
            'type': 'ir.actions.act_window',
            'res_id': self.id,
            'target': 'new',
        }

    def button_copy(self):
        return {
            "type": "ir.actions.do_nothing",
        }

