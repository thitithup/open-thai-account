# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'INECO Thai Account',
    'version': '1.0',
    'depends': ["base", "base_import",
                "account", "purchase", "sale", "sale_management", "stock", "account_debit_note", "ineco_account_base",
                "ineco_account_period", "hr", "sale_stock"],
    'author': 'INECO LTD.,PART.',
    'category': 'INECO/Thai Account',
    'description': """
Feature: 
Thailand Accounting
    """,
    'website': 'http://www.ineco.co.th',
    'data': [
        "data/data.xml",
        "data/account_invoice_report_view.xml",
        "data/admin_account_report_view.xml",
        # "data/report.xml",
        "data/sequence.xml",
        "data/wht_data.xml",
        "security/security.xml",
        "security/group.xml",
        # "security/ir.model.access.csv",
        'views/invoice_views.xml',
        "wizard/pay_wizard_view.xml",
        "wizard_back_tax_payment/wizard_back_payment_view.xml",
        "wizard_back_tax/wizard_back_view.xml",
        "wizard_sale_deposit/sale_wizard_deposit_view.xml",
        "refund_wizard/account_invoice_refund_view.xml",
        "wizard_merge_vendor_bill/picking_merge_vendor_bill_view.xml",

        "views/res_config_settings_views.xml",
        "views/account_billing_view.xml",
        "views/account_customer_deposit_view.xml",
        "views/account_customer_payment_view.xml",
        "views/account_cheque_view.xml",
        "views/account_wht_view.xml",
        "views/partner_view.xml",
        "views/move_view.xml",
        "views/account_vat_view.xml",
        # "views/account_tax.xml",
        "views_move/account_move_view.xml",

        'views/account_vender_deposit_view.xml',
        'views/account_vender_payment_view.xml',
        'views/account_vat_purchase_view.xml',
        'views/account_billing_vendor_view.xml',

        "views_move/account_move_pay_view.xml",
        "views_move/account_move_sale_view.xml",
        "views_move/account_move_receive_view.xml",
        "views_move/account_move_general_view.xml",

        "views/account_journal_view.xml",

        "models_petty_cash/wizard/kk_petty_cash_make_pay.xml",
        "petty_cash_views/petty_cash.xml",
        "petty_cash_views/account_pay_in_petty_cash_view.xml",
        "petty_cash_views/invoice_petty_cash_view.xml",
        "views/res_company_views.xml",
        "views/sale_order_views.xml",

        "views/stock_picking_view.xml",
        "views/stock_picking_type_insert_view.xml",

        "views/purchase_order_view.xml",
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': True,
    'images': [],
    'license': 'LGPL-3',
}
