# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class stock_picking_type(models.Model):
    _inherit = 'stock.picking.type'

    # สร้างใบตั้งหนี้จากใบสั่งซื้อ
    create_invoice_vendor = fields.Boolean(string='Create Invoice Vendor', default=False)
    create_invoice_customer = fields.Boolean(string='Create Invoice Customer', default=False)
