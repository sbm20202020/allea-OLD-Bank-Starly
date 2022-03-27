# See LICENSE file for full copyright and licensing details.
{
    'name': 'Microsoft Azure SSO Integration',
    'version': '13.0',
    'license': 'LGPL-3',
    'summary': 'Odoo provide interactive feature to integrate or synchronized with Microsoft Azure.',
    'description': """Odoo provide interactive feature to integrate or synchronized with Microsoft Azure. 
		Using this module, you can sync your Microsoft Azure users with Odoo seamlessly. 
        Microsoft Azure SSO Integration
		Microsoft Azure Odoo SSO Integration
		Odoo Microsoft Azure
		odoo on azure
		azure odoo
		odoo microsoft sso
		odoo microsoft azure integration
		microsoft azure odoo sso
		microsoft odoo azure portal
		Odoo Office365 Calendar Integration
		Odoo Office365 Contacts Integration
		Microsoft Users Odoo Integration Base Module
		Microsoft Users odoo integration module
		Odoo Integration with Microsoft Users
		Odoo with Microsoft Users
		Login using Microsoft Account
		Odoo Login using Microsoft Account
		Odoo Integration signin with Microsoft Account
		Odoo Integration signin using Microsoft Account
		odoo integration module with Microsoft Users
		Microsoft User with odoo integration
		Odoo Integration Base Module
		Odoo Integration Module
		Odoo Microsoft Azure
		Office 365
		Odoo Office365
		odoo microsoft account
		Microsoft Azure SSO
		Microsoft SSO
		Microsoft SSO Integration
		Microsoft Azure Single sign-on
		Azure SSO
		Microsoft
    """,
    'category': 'Extra Tools',
    'author': 'Serpent Consulting Services Pvt. Ltd.',
    'website': 'https://www.serpentcs.com',
    'depends': ['auth_oauth'],
    'data': [
        'views/res_config.xml',
        'views/oauth_provider.xml',
        'data/auth_oauth_data.xml',
    ],
    'images': ['static/description/microsoft_azure.png'],
    "live_test_url": "https://youtu.be/sU3RiBHKDvM",
    'external_dependencies': {'python': ['simplejson']},
    'installable': True,
    'auto_install': False,
    'price': 129,
    'currency': 'EUR'
}
