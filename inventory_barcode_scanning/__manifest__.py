{
    'name': 'Barcode scanning in Inventory',
    'version': '13.0.0.1',
    'summary': 'Barcode Support in Stock Picking.',
    'author': 'Solopov Nikita',
    'depends': ['stock'],
    'category': 'Inventory',
    'data': [
        'views/stock_move_views.xml',
        'views/production_lot_views.xml',
        'views/stock_picking_views.xml'
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'AGPL-3',
}
