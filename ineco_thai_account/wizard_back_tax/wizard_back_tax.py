# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
from datetime import datetime

from odoo import api, fields, models, exceptions
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError


class WizardBackTax(models.TransientModel):
    _name = "wizard.back.tax"
    _inherit = ['mail.thread']

    @api.depends('item_ids')
    def _get_amount_tax(self):
        amount_tax = 0.0
        for tax in self.item_ids:
            amount_tax += tax.amount_tax
        self.amount_tax_total = amount_tax

    item_ids = fields.One2many('wizard.back.tax.line', 'order_id', string='Order Lines')
    invoice_id = fields.Many2one('account.move', string='Invoice', ondelete="restrict")
    name = fields.Char(string='เลขที่ใบกำกับภาษี', required=False, copy=False, tracking=True)
    docdat = fields.Date(string='ลงวันที่', required=True, tracking=True)
    vatprd = fields.Date(string='วันที่ยื่น', required=True)
    partner_id = fields.Many2one('res.partner', 'พาร์ทเนอร์', required=True)
    taxid = fields.Char(string='เลขประจำตัวผู้เสียภาษี', required=True, copy=True)
    depcod = fields.Char(string='รหัสสาขา', size=5, required=True, copy=True)
    amount_untaxed = fields.Float(string='ยอดก่อนภาษี')
    amount_tax = fields.Float(string='ภาษี')
    amount_total = fields.Float(string='ยอดเงินรวม')
    account_id = fields.Many2one('account.account', string='Account')
    ineco_vat = fields.Many2one('ineco.account.vat', string='ineco_vat', ondelete='cascade')

    amount_tax_total = fields.Float(string='ยอดรวมภาษี', compute='_get_amount_tax')
    journal_id = fields.Many2one('account.journal', string=u'สมุดรายวัน', required=False)

    type = fields.Selection([
        ('1', u'แยกใบกำกับ'),
        ('2', u'รวมใบกำกับ'),
    ], default=False, string=u'ประเภทการกลับ')

    @api.model
    def default_get(self, fields):
        res = super(WizardBackTax, self).default_get(
            fields)
        ineco_account_vat_obj = self.env['ineco.account.vat']
        line_ids = self.env.context.get('active_ids', False)
        tax = ineco_account_vat_obj.browse(line_ids)

        # if tax.tax_purchase_ok:
        #     raise UserError("ต้องเป็นภาษีพัก")
        items = []
        for line in tax:
            if not line.vatprd:
                line_data = {
                    'order_id': self.id,
                    'ineco_vat': line.id,
                    'account_id': line.account_id.id,
                    'invoice_id': line.invoice_id.id,
                    'name': line.name,
                    'docdat': line.docdat,
                    'partner_id': line.partner_id.id,
                    'taxid': line.taxid,
                    'depcod': line.depcod,
                    'amount_untaxed': line.amount_untaxed,
                    'amount_tax': line.amount_tax,
                    'amount_total': line.amount_total
                }
                items.append([0, 0, line_data])

        res['invoice_id'] = tax[0].invoice_id.id
        res['name'] = tax[0].name
        res['docdat'] = tax[0].docdat
        res['partner_id'] = tax[0].partner_id.id
        res['depcod'] = tax[0].depcod
        res['taxid'] = tax[0].taxid
        res['amount_untaxed'] = tax[0].amount_untaxed
        res['amount_tax'] = tax[0].amount_tax
        res['amount_total'] = tax[0].amount_total
        res['account_id'] = tax[0].account_id.id
        res['ineco_vat'] = tax[0].id
        res['item_ids'] = items

        return res

    def create_po_tax(self):
        for line in self.item_ids:
            if line.partner_id.id != self.partner_id.id:
                raise UserError(("เจ้าหนี้ไม่ตรงกัน"))

        move = self.env['account.move']
        iml = []
        vats = []

        period_id = self.env['ineco.account.period'].finds(dt=self.vatprd)
        if self.type == '2':
            for vat in self:
                data = {
                    'vat_type': 'purchase',
                    'name': vat.name,
                    'docdat': vat.docdat,
                    'vatprd': self.vatprd,
                    'period_id': period_id.id,
                    'partner_id': vat.partner_id.id,
                    'partner_name': vat.partner_id.name,
                    'taxid': vat.taxid,
                    'depcod': vat.depcod,
                    'amount_untaxed': self.amount_untaxed,
                    'amount_tax': self.amount_tax_total,
                    'amount_total': self.amount_total,
                    'invoice_id': vat.invoice_id.id,
                    'tax_purchase_ok': True,
                    'tax_purchase_wait_ok': False,
                }
                vats.append((0, 0, data))
        else:
            for vat in self.item_ids:
                data = {
                    'vat_type': 'purchase',
                    'name': vat.name,
                    'docdat': vat.docdat,
                    'vatprd': self.vatprd,
                    'period_id': period_id.id,
                    'partner_id': vat.partner_id.id,
                    'partner_name': vat.partner_id.name,
                    'taxid': vat.taxid,
                    'depcod': vat.depcod,
                    'amount_untaxed': vat.amount_untaxed,
                    'amount_tax': vat.amount_tax,
                    'amount_total': vat.amount_total,
                    'invoice_id': vat.invoice_id.id,
                    'tax_purchase_ok': True,
                    'tax_purchase_wait_ok': False,
                }
                vats.append((0, 0, data))

        vat_purchase_account_id = self.env.company.vat_purchase_account_id.id
        move_data_vals_0 = {
            'name': u'ยื่นภาษีซื้อ',
            'partner_id': False,
            'debit': self.amount_tax_total,
            'credit': 0.0,
            'payment_id': False,
            'account_id': vat_purchase_account_id,
            'vat_ids': vats
        }
        iml.append((0, 0, move_data_vals_0))

        for vat in self.item_ids:
            move_data_vals = {
                'partner_id': vat.partner_id.id,
                'debit': 0.0,
                'credit': vat.amount_tax,
                'payment_id': False,
                'account_id': vat.account_id.id,
                'ineco_vat': vat.ineco_vat.id
            }
            if vat.ineco_vat.vatprd:
                raise UserError(f'ไม่สามารภกลับภาษีซื้อได้ เนื่องจากมีการนำรายการนี้ไม่นำส่งแล้ว {vat.name}')
            vat.ineco_vat.write({'vatprd': self.vatprd})
            vat.invoice_id.write({'ineco_reconciled_tax': vat.ineco_vat.id})
            iml.append((0, 0, move_data_vals))

        move_vals = {
            'ref': u'ยื่นภาษีซื้อ',
            'date': self.vatprd,
            'company_id': self.env.user.company_id.id,
            'journal_id': self.journal_id.id,
        }
        new_move = move.create(move_vals)
        new_move.sudo().write({'line_ids': iml})
        new_move.post()
        for vat in self.item_ids:
            vat.ineco_vat.write({'move_id': new_move.id})

        view_ref = self.env['ir.model.data'].check_object_reference('account',
                                                                  'view_move_form')
        view_id = view_ref and view_ref[1] or False,
        if view_ref:
            return {
                'type': 'ir.actions.act_window',
                'name': 'ineco.account.move.form',
                'res_model': 'account.move',
                'res_id': new_move.id,

                'view_mode': 'form',
                'view_id': view_id,
                'target': 'current',
                'nodestroy': True,
            }
        return {'type': 'ir.actions.act_window_close'}


class WizardBackTaxLine(models.TransientModel):
    _name = 'wizard.back.tax.line'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.depends('amount_untaxed')
    def _compute_amount_tax(self):
        for line in self:
            if line.amount_untaxed or line.amount_tax:
                line.amount_tax = line.amount_untaxed * 0.07

    @api.depends('amount_untaxed', 'amount_tax')
    def _compute_amount_total(self):
        for line in self:
            if line.amount_untaxed or line.amount_tax:
                line.amount_total = line.amount_untaxed + line.amount_tax

    order_id = fields.Many2one('wizard.back.tax', string='Line Tax', ondelete='cascade')

    name = fields.Char(string='เลขที่ใบกำกับภาษี', required=True, copy=False, tracking=True)
    docdat = fields.Date(string='ลงวันที่', required=True, tracking=True)
    partner_id = fields.Many2one('res.partner', 'พาร์ทเนอร์', required=True)
    taxid = fields.Char(string='เลขประจำตัวผู้เสียภาษี', size=13, required=True, copy=True)
    depcod = fields.Char(string='รหัสสาขา', size=5, required=True, copy=True)
    amount_untaxed = fields.Float(string='ยอดก่อนภาษี')
    amount_tax = fields.Float(string='ภาษี',
                              compute='_compute_amount_tax',
                              store=True)
    amount_total = fields.Float(string='ยอดเงินรวม',
                                compute='_compute_amount_total',
                                store=True)
    account_id = fields.Many2one('account.account', string='Account')
    invoice_id = fields.Many2one('account.move', string='Invoice', ondelete="restrict")
    ineco_vat = fields.Many2one('ineco.account.vat', string='ineco_vat', ondelete='cascade')

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        for line in self:
            line.taxid = line.partner_id.vat
            line.depcod = line.partner_id.branch_no
