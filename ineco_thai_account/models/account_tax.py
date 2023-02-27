# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountTax(models.Model):

    _inherit = 'account.tax'

    tax_break = fields.Boolean(string=u'ภาษีพัก', default=False)
