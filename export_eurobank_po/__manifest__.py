{
    'name': 'Eurobank purchase order import',
    'summary': '',
    'description': """Module allows you import purchase order in specific txt format for Eurobank""",
    'version': '13.0.0.0',
    'author': 'Solopov Nikita',
    'license': 'OPL-1',
    'depends': [
        'purchase'
    ],
    'data': [
        'views/purchase_order_views.xml',
        'wizard/wizard_views.xml',
    ],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
