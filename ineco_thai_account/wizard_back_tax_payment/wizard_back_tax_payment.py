# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
from datetime import datetime

from odoo import api, fields, models, exceptions
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError


class WizardBackTaxPayment(models.TransientModel):
    _name = "wizard.back.tax.payment"
    _inherit = ['mail.thread']

    @api.depends('item_ids')
    def _get_amount_tax(self):
        amount_tax = 0.0
        for tax in self.item_ids:
            amount_tax += tax.amount_tax
        self.amount_tax_total = amount_tax

    item_ids = fields.One2many('wizard.back.tax.payment.line', 'order_id', string='Order Lines')

    @api.model
    def default_get(self, fields):
        res = super(WizardBackTaxPayment, self).default_get(
            fields)
        ineco_payment_obj = self.env['ineco.supplier.payment']
        line_ids = self.env.context.get('active_ids', False)
        payment_objs = ineco_payment_obj.browse(line_ids)
        items = []
        for line in payment_objs.line_ids:
            ineco_account_vat_obj = self.env['ineco.account.vat'].search([
                ('invoice_id', '=', line.name.move_id.id),
                ('move_line_id', '!=', False),
                ('tax_purchase_wait_ok', '=', True)
            ])

            if ineco_account_vat_obj:
                line_data = {
                    'order_id': self.id,
                    'ineco_vat': ineco_account_vat_obj.id,
                    'account_id': ineco_account_vat_obj.account_id.id,
                    'name': ineco_account_vat_obj.name,
                    'docdat': ineco_account_vat_obj.docdat,
                    'partner_id': ineco_account_vat_obj.partner_id.id,
                    'taxid': ineco_account_vat_obj.taxid,
                    'depcod': ineco_account_vat_obj.depcod,
                    'amount_untaxed': ineco_account_vat_obj.amount_untaxed,
                    'amount_tax': ineco_account_vat_obj.amount_tax,
                    'amount_total': ineco_account_vat_obj.amount_total
                }
                items.append([0, 0, line_data])
        res['item_ids'] = items
        return res

    def create_back_payment_tax(self):
        ineco_payment_obj = self.env['ineco.supplier.payment']
        line_ids = self.env.context.get('active_ids', False)
        payment_objs = ineco_payment_obj.browse(line_ids)
        for line in self.item_ids:
            period_id = self.env['ineco.account.period'].finds(dt=line.docdat)
            line_data = {
                'supplier_payment_id': payment_objs.id,
                'reconciliation_in': line.ineco_vat.id,
                'name': line.name,
                'period_id': period_id.id,
                'docdat': line.docdat,
                'partner_id': line.partner_id.id,
                'taxid': line.taxid,
                'depcod': line.depcod,
                'amount_untaxed': line.amount_untaxed,
                'amount_tax': line.amount_tax,
                'amount_total': line.amount_total
            }
            ineco_account_vat_obj = self.env['ineco.account.vat']

            vat = ineco_account_vat_obj.search(
                [('supplier_payment_id', '=', payment_objs.id), ('reconciliation_in', '=', line.ineco_vat.id)])
            if not vat:
                ineco_account_vat_obj.create(line_data)


class WizardBackTaxPaymentLine(models.TransientModel):
    _name = 'wizard.back.tax.payment.line'
    _inherit = ['mail.thread']

    order_id = fields.Many2one('wizard.back.tax.payment', string='Line Tax', ondelete='cascade')
    name = fields.Char(string='เลขที่ใบกำกับภาษี', required=True, copy=False, tracking=True)
    docdat = fields.Date(string='ลงวันที่', required=True, tracking=True)
    partner_id = fields.Many2one('res.partner', 'พาร์ทเนอร์', required=True)
    taxid = fields.Char(string='เลขประจำตัวผู้เสียภาษี', size=13, required=True, copy=True)
    depcod = fields.Char(string='รหัสสาขา', size=5, required=True, copy=True)
    amount_untaxed = fields.Float(string='ยอดก่อนภาษี')
    amount_tax = fields.Float(string='ภาษี')
    amount_total = fields.Float(string='ยอดเงินรวม')
    account_id = fields.Many2one('account.account', string='Account')
    ineco_vat = fields.Many2one('ineco.account.vat', string='ineco_vat', ondelete='cascade')

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        for line in self:
            line.taxid = line.partner_id.vat
            line.depcod = line.partner_id.branch_no
