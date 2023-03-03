# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountTax(models.Model):

    _inherit = 'account.tax'

    tax_break = fields.Boolean(string=u'ภาษีพัก', default=False)
    account_id = fields.Many2one('account.account', string=u'Account', compute='_compute_account_id')

    def _compute_account_id(self):
        for rec in self:
            for tax in rec.invoice_repartition_line_ids:
                if tax.account_id:
                    rec.account_id = tax.account_id.id
