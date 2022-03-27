{
    'name': 'Agreements',
    'version': '13.0.0.1.0',
    'category': 'Invoicing',
    'author': 'Solopov Nikita',
    'website': 'https://icode.by',
    'depends': [
        'base',
        'mail',
        'purchase_requisition',
        'product',
        'account',
        'purchase',
        'contacts',
    ],
    'data': [
        'security/rules.xml',
        'security/ir.model.access.csv',
        'data/agreement_type.xml',
        'data/sequence.xml',
        'views/agreement_views.xml',
        'views/purchase_order_views.xml',
        'views/partner_views.xml',
    ],
    'auto_install': False,
    'installable': True,
}
