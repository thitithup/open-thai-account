# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'INECO - Sale Service',
    'version': '0.1',
    'summary': 'Service order and project management',
    'sequence': 100,
    'description': """
    """,
    'category': 'INECO/Modules',
    'website': 'https://www.ineco.co.th',
    'images': [],
    'depends': ['sale', 'sale_project', 'sale_timesheet', 'purchase', 'stock', 'project', 'hr_expense', 'analytic',
                'sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_view.xml',
        'views/stock_picking_type_view.xml',
        'views/stock_picking_view.xml',

        'wizard_select_timesheet/wizard_select_timesheet.xml',

        'views/project_project_view.xml',
        'views/analytic_view.xml',
        'security/security.xml',
        'views/res_company_view.xml',

        'views/hr_expense_sheet_views.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    # 'post_init_hook': '_account_post_init',
    'license': 'LGPL-3',
}
