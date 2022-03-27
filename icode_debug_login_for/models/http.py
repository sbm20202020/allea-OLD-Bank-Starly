from odoo import http


class OverridedRootFromHttp(http.Root):
    def setup_db(self, httprequest):
        db = httprequest.session.db
        # Check if session.db is legit
        if db:
            if db not in http.db_filter([db], httprequest=httprequest):
                httprequest.session.logout()
                db = None
        if not db:
            if 'db' in httprequest.args:
                db = httprequest.args['db']
                httprequest.session.db = db
        else:
            httprequest.session.db = http.db_monodb(httprequest)


http.Root.setup_db = OverridedRootFromHttp.setup_db






