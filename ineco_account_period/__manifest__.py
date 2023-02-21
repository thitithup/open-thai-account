# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Ineco Account Period',
    'version': '0.1',
    'summary': 'Account Fiscal Year and Period',
    'sequence': 1000,
    'description': """    
    """,
    'category': 'INECO',
    'website': 'https://www.ineco.co.th',
    'images': [],
    'depends': ["account","sale"],
    'data': [
        'security/security.xml',
        'views/account_fiscalyear_view.xml',
        'views/account_period_view.xml',
        'views/account_move_view.xml',
    ],
    'demo': [
    ],
    'qweb': [
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
