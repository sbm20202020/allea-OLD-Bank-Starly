import datetime
import logging

from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)

TOKEN_LIFETIME = 60

class AutoLoginController(http.Controller):
    @http.route('/custom_login', type="http", auth="public")
    def login_by_token(self, **kw):
        if 'token' in kw.keys():
            # Check
            token_active_time = datetime.timedelta(seconds=TOKEN_LIFETIME)
            user = request.env['res.users'].sudo().search([('login_for_token', '=', kw['token'])], limit=1)
            if str(datetime.datetime.now() - token_active_time) < str(user.login_for_token_birth_time):
                if not user:
                    _logger.error("Your token lifetime is expired",)
                    return Response("Your token lifetime is expired", status=401)

                # Authenticate
                request.session.authenticate(request.env.cr.dbname, user.login, kw['token'])
                _logger.info("Login was successfully completed for <%s> as user <%s> ",
                             kw['admin_name'],
                             user.name
                             )
                # Clean fields after login
                user.update({'login_for_token': None, 'login_for_link': None})
                # Redirect
                redirect_url = '/web'
                _logger.debug(redirect_url)
                return http.local_redirect(redirect_url)
            else:
                return Response("Your token lifetime is expired", status=401)

