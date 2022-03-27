from odoo import api, SUPERUSER_ID

BAD_COMPANIES = ()


def init_remove_companies(cr, registry):
    """ Sets the company name as the default value for the initiating
    party name on all existing companies once the module is installed. """
    env = api.Environment(cr, SUPERUSER_ID, {})
    for company in env['res.company'].search([]):
        pass
        # company.sepa_initiating_party_name = sanitize_communication(company.name)
