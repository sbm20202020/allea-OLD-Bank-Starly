"""
EU includes:
    Austria, Belgium, Bulgaria, Great Britain, Hungary,
    Germany, Greece, Denmark, Ireland, Spain, Italy, Cyprus,
    Latvia, Lithuania, Luxembourg, Malta, the Netherlands,
    Poland, Portugal, Romania, Slovakia, Slovenia, Finland,
    France, Croatia, Czech Republic, Sweden and Estonia.
"""

EU_COUNTRY_CODES = {
    "AT",
    "BE",
    "BG",
    "CY",
    "CZ",
    "DE",
    "DK",
    "EE",
    "ES",
    "FI",
    "FR",
    "GB",
    "GR",
    "HR",
    "HU",
    "IE",
    "IT",
    "LT",
    "LU",
    "LV",
    "MT",
    "NL",
    "PL",
    "PT",
    "RO",
    "SE",
    "SI",
    "SK",
}


def post_init_hook(cr, registry):
    """Rewrite ICP's to force groups"""
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    country_ids = env['res.country'].search([])
    for country_id in country_ids:
        is_in_eu = country_id.is_in_eu
        country_id_code = country_id.code
        if country_id_code in EU_COUNTRY_CODES and not is_in_eu:
            country_id.is_in_eu = True
        elif country_id_code not in EU_COUNTRY_CODES and is_in_eu:
            country_id.is_in_eu = False
