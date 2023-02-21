# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
import time

from odoo.exceptions import UserError


class InecoCheque(models.Model):
    _name = 'ineco.cheque'
    _description = 'Cheque'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', ]

    name = fields.Char(string='เลขที่เช็ค', required=True, tracking=True)
    cheque_date = fields.Date(string='ลงวันที่', required=True, tracking=True)
    cheque_date_reconcile = fields.Date(string='วันตัดธนาคาร', tracking=True)
    account_bank_id = fields.Many2one('account.journal', string='สมุดธนาคาร', required=True, copy=False,
                                      index=True, tracking=True)
    bank = fields.Many2one('res.bank', string='ธนาคาร', readonly=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string='พาร์ทเนอร์', required=True, tracking=True)
    amount = fields.Float(string='ยอดเงิน', digits=(12, 2), required=True)
    type = fields.Selection([('out', 'เช็คจ่าย'), ('in', 'เช็ครับ')], string='ประเภทเช็ค', required=True,
                            tracking=True)
    ref_bank = fields.Char(u'อ้างอิงธนาคารเช็ครับ')
    note = fields.Text(string='หมายเหตุ')
    date_cancel = fields.Datetime(string='Date Cancel', tracking=True)
    date_done = fields.Datetime(string='Date Done', tracking=True)
    date_pending = fields.Datetime(string='Date Pending', tracking=True)
    date_reject = fields.Datetime(string='Date Reject', tracking=True)
    date_assigned = fields.Datetime(string='Date Assigned', tracking=True)
    account_receipt_id = fields.Many2one('account.account', related='account_bank_id.default_account_id',
                                         string='ผังบัญชีธนาคาร (รับ)')
    account_pay_id = fields.Many2one('account.account', related='account_bank_id.default_account_id',
                                     string='ผังบัญชีธนาคาร (จ่าย)')
    move_line_id = fields.Many2one('account.move.line', string='Move Line', ondelete='restrict')
    move_id = fields.Many2one('account.move', string="สมุดรายวัน", ondelete='restrict')
    customer_payment_id = fields.Many2one('ineco.customer.payment', string='Customer Payment', ondelete="restrict")
    customer_deposit_id = fields.Many2one('ineco.customer.deposit', string='Customer Deposit', ondelete="restrict")

    supplier_payment_id = fields.Many2one('ineco.supplier.payment', string='Supplier Payment', ondelete="restrict")
    supplier_deposit_id = fields.Many2one('ineco.supplier.deposit', string='Supplier Deposit', ondelete="restrict")

    pay_expense_id = fields.Many2one('ineco.pay.in.petty.cash', string='Expense Cash', ondelete="restrict")

    active = fields.Boolean(string='Active', default=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('cancel', 'Cancelled'),
        ('assigned', 'Assigned'),
        ('pending', 'Pending'),
        ('reject', 'Reject'),
        ('done', 'Done'),
    ], string='สถานะ', default='draft', readonly=True, tracking=True)

    company_id = fields.Many2one('res.company', string='Company', store=True, readonly=True, change_default=True,
                                 default=lambda self: self.env.company)

    _sql_constraints = [
        ('name_cheque_uniq', 'unique (name,cheque_date)', u'ห้ามเช็คซ้ำ')
    ]

    @api.model
    def daily_update_account_bank(self):
        cheques = self.env['ineco.cheque'].search([('bank', '=', False), ])
        for cheque in cheques:
            cheque.onchange_account_bank_id()

    @api.onchange('account_bank_id')
    def onchange_account_bank_id(self):
        if self.account_bank_id:
            self.bank = self.account_bank_id.bank_id.id

    def action_cancel_draft(self):
        if self.customer_payment_id.state == 'cancel':
            self.customer_payment_id.button_draft()
        self.state = 'draft'

    def action_assigned(self):
        self.state = 'assigned'
        self.date_assigned = time.strftime('%Y-%m-%d %H:%M:%S')

    def pending_cheque(self):
        self.state = 'pending'
        self.date_pending = time.strftime('%Y-%m-%d %H:%M:%S')

    def reject_cheque(self):
        self.state = 'reject'
        self.date_reject = time.strftime('%Y-%m-%d %H:%M:%S')

    def cancel_cheque(self):
        if self.move_id:
            self.move_id.button_cancel()
            self.move_id.unlink()
        self.state = 'cancel'
        self.date_cancel = time.strftime('%Y-%m-%d %H:%M:%S')

    def action_done_draft(self):
        if self.move_id:
            self.move_id.button_cancel()
            self.move_id.posted_before =False
            self.move_id.unlink()
        self.cheque_date_reconcile = False
        self.state = 'cancel'

    def action_done(self):
        if not self.cheque_date_reconcile:
            raise UserError("กรุณาระบุวันที่ผ่านเช็ค")
        # ตัดเจ้านี้เมื่อผ่านเช็ค
        if self.customer_payment_id.state == 'draft':
            self.customer_payment_id.button_post()
        if self.customer_payment_id.state == 'cancel':
            raise UserError("Customer Payment ถูกยกเลิก")
        move_pool = self.env['account.move']
        move_line_pool = self.env['account.move.line']
        params = self.env['ir.config_parameter'].sudo()
        journal = self.env['account.journal'].search([('type', '=', 'general')])[0]
        date_reconcile = False
        iml = []
        if not self.cheque_date_reconcile:
            date_reconcile = time.strftime('%Y-%m-%d')
        else:
            date_reconcile = self.cheque_date_reconcile
        if self.type == 'out':
            new_voucher_no = self.env['ir.sequence'].next_by_code('ineco.cheque.out')
            # new_voucher_no = 'QS' + self.name
            move_cheque = {
                'name': new_voucher_no,
                'ref': self.name,
                'journal_id': journal.id,
                'type': 'out_invoice',
                'narration': self.note,
                'partner_id': self.partner_id.id,
                'date':self.cheque_date_reconcile
            }
            move_line_detail = {
                'name': new_voucher_no,
                'debit': 0.0,
                'credit': self.amount,
                'account_id': self.account_pay_id.id,
                'journal_id': journal.id,
                'partner_id': self.partner_id.id,
                'date': date_reconcile,
            }
            iml.append((0, 0, move_line_detail))
            cheque_purchase_account_id = self.env.company.cheque_purchase_account_id.id
            move_line_detail = {
                'name': self.move_line_id.account_id.name or False,
                'debit': self.amount,
                'credit': 0.0,
                'account_id': cheque_purchase_account_id,  # self.move_line_id.account_id.id,
                'journal_id': journal.id,
                'partner_id': self.partner_id.id,
                'date': date_reconcile,
            }
            iml.append((0, 0, move_line_detail))
            move_id = move_pool.create(move_cheque)
            move_id.write({'name': new_voucher_no})
            move_id.sudo().write({'line_ids': iml})
            move_id.post()

            self.state = 'done'
            self.date_done = time.strftime('%Y-%m-%d %H:%M:%S')
            self.move_id = move_id.id
            self.cheque_date_reconcile = date_reconcile

        if self.type == 'in':
            new_voucher_no = self.env['ir.sequence'].next_by_code('ineco.cheque.in')
            # new_voucher_no = 'QR' + self.name
            move_cheque = {
                'name': new_voucher_no,
                'ref': self.name,
                'type': 'out_invoice',
                'journal_id': journal.id,
                'narration': self.note,
                'partner_id': self.partner_id.id,
            }
            move_line_detail = {
                'name': new_voucher_no,
                'debit': self.amount,
                'credit': 0.0,
                'account_id': self.account_receipt_id.id,
                'journal_id': journal.id,
                'partner_id': self.partner_id.id,
                'date': date_reconcile,
            }
            iml.append((0, 0, move_line_detail))
            cheque_sale_account_id = self.env.company.cheque_sale_account_id.id
            move_line_detail = {
                'name': self.move_line_id.account_id.name or '',
                'debit': 0.0,
                'credit': self.amount,
                'account_id': cheque_sale_account_id,
                # self.move_line_id.account_id.id,  # line.journal_id.default_debit_account_id.id,
                'journal_id': journal.id,
                'partner_id': self.partner_id.id,
                'date': date_reconcile,
            }
            iml.append((0, 0, move_line_detail))
            move_id = move_pool.create(move_cheque)
            move_id.write({'name': new_voucher_no})
            move_id.sudo().write({'line_ids': iml})
            move_id.post()
            self.state = 'done'
            self.date_done = time.strftime('%Y-%m-%d %H:%M:%S')
            self.move_id = move_id.id
            self.cheque_date_reconcile = date_reconcile
