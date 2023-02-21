# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'INECO Geography',
    'version': '1.0',
    'depends': ["base", "mail", "contacts"],
    'author': 'INECO LTD.,PART.',
    'category': 'INECO',
    'description': """
Feature: 
Thailand Geography
    """,
    'website': 'http://www.ineco.co.th',
    'data': [
        'data/update.xml',
        'views/partner_view.xml',
        'security/security.xml',
        'data/ineco.geography.csv',
        'data/ineco.province.csv',
        'data/ineco.amphur.csv',
        'data/ineco.district.csv',
        'data/ineco.zipcode.csv',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': True,
    'images': [],
    'license': 'LGPL-3',
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
