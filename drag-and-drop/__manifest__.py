# -*- coding: utf-8 -*-
{
    'name': "Drag & Drop Multiple Files",

    'summary': """
        Drag and Drop Attachments without limits. Upload Screenshots easily.
    """,

    'author': "Andreas Wyrobek",
    'website': "http://www.cytex.cc",

    'category': 'Technical Settings',
    'version': '13.0.1',
	
	'images': ['images/main_screenshot.png'],

    # any module necessary for this one to work correctly
    'depends': ['base', 'documents', 'web'],

    # always loaded
    'data': [
        # 'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [],

    'installable': True,
    'application': True,
    'auto_install': False,
}
