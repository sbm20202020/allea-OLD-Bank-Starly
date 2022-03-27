{
    'name': 'Dymo barcode reports',
    'version': '1.1',
    'summary': 'Inventory, Logistics, Warehousing',
    'depends': ['product', 'stock'],
    'category': 'Operations',
    'data': [
        'report/stock_report_views.xml',
        'report/report_lot_barcode_short.xml',
        'report/report_lot_barcode_long.xml',
        'report/report_product_label_short.xml',
        'report/report_product_label_long.xml',
        'data/report_paperformat_data.xml',
        'views/stock_production_lot_views.xml',
        'views/res_company_view.xml'
    ],
    'installable': True,
}
