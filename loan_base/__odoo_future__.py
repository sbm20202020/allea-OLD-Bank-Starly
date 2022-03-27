# standard import
from datetime import date, datetime

# odoo import
from odoo import fields
from odoo.fields import DATE_LENGTH
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
from odoo.release import version_info


def to_date(value):
    """
    Attempt to convert ``value`` to a :class:`date` object.

    This function can take as input different kinds of types:
        * A falsy object, in which case None will be returned.
        * A string representing a date or datetime.
        * A date object, in which case the object will be returned as-is.
        * A datetime object, in which case it will be converted to a date object and all\
                    datetime-specific information will be lost (HMS, TZ, ...).

    :param value: value to convert.
    :return: an object representing ``value``.
    :rtype: date
    """
    if not value:
        return None
    if isinstance(value, date):
        if isinstance(value, datetime):
            return value.date()
        return value
    value = value[:DATE_LENGTH]
    return datetime.strptime(value, DATE_FORMAT).date()


if version_info[0] >= 12:
    to_date = fields.Date.to_date
