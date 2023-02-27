# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Ineco Account Base',
    'version': '0.1',
    'summary': 'Account Base',
    'sequence': 1000,
    'description': """    
1. ต้องเปลี่ยน Chart ของ Journal ทุกตัว Invoice, Cash, Bank
2. ต้องเปลี่ยน Company Property (Account Receivable, Account Payable, Category Income, Category Expense)
    """,
    'category': 'INECO',
    'website': 'https://www.ineco.co.th',
    'images': [],
    'depends': ["account"],
    'data': [
        # 'views/account_menu.xml',
        'views/account_account_view.xml',
    ],
    'demo': [
    ],
    'qweb': [
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
