# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools
from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError
from collections import defaultdict


class ResCompany(models.Model):
    _inherit = 'res.company'
    _description = 'Company Data'

    sale_margin_profit = fields.Float(string='Sale Margin (%)', default=10, digits=(12, 2))
