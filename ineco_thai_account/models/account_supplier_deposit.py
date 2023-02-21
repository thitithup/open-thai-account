# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    deposit_id = fields.Many2one('ineco.supplier.deposit', string=u'เงินมัดจำ', tracking=True)


class InecoSupplierDeposit(models.Model):
    _name = 'ineco.supplier.deposit'
    _description = 'Supplier Deposit'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    @api.depends('line_ids')
    def _get_receipts(self):
        for receipt in self:
            receipt.amount_receipt = 0.0
            receipt.amount_deposit = 0.0
            for line in receipt.line_ids:
                untaxed = 0.0
                tax = 0.0
                if receipt.tax_type == 'percent':
                    tax = line.amount_untaxed * receipt.amount_type_tax / 100
                    line.amount_tax = tax
                    line.amount_receipt = line.amount_untaxed + tax
                else:
                    tax = line.amount_untaxed - (line.amount_untaxed * 100) / (100 + receipt.amount_type_tax)
                    line.amount_tax = tax
                    line.amount_receipt = line.amount_untaxed - tax
                receipt.amount_receipt += round(line.amount_receipt, 2)
                receipt.amount_deposit += round(line.amount_untaxed, 2)

    @api.depends('wht_ids')
    def _get_wht(self):
        for receipt in self:
            receipt.amount_wht = 0.0
            for wht in receipt.wht_ids:
                receipt.amount_wht += wht.tax

    @api.depends('cheque_ids')
    def _get_cheque(self):
        for receipt in self:
            receipt.amount_cheque = 0.0
            for cheque in receipt.cheque_ids:
                receipt.amount_cheque += cheque.amount

    @api.depends('vat_ids')
    def _get_vat(self):
        for receipt in self:
            receipt.amount_vat = 0.0
            for vat in receipt.vat_ids:
                receipt.amount_vat += vat.amount_tax

    @api.depends('other_ids')
    def _get_other(self):
        for receipt in self:
            receipt.amount_other = 0.0
            for vat in receipt.other_ids:
                receipt.amount_other += vat.amount

    @api.depends('amount_receipt')
    def _get_payment(self):
        for receipt in self:
            receipt.amount_residual = receipt.amount_receipt
            receipt_total = 0.0
            if receipt.payment_ids:
                for payment in receipt.payment_ids:
                    if payment.invoice_id and payment.invoice_id.state not in ('cancel'):
                        receipt_total += payment.amount_receipt
                    if payment.payment_id and payment.payment_id.state not in ('cancel'):
                        receipt_total += payment.amount_receipt
            receipt.amount_residual = receipt.amount_deposit - receipt_total

    @api.depends('supplier_deposit_pay_ids', 'amount_deposit', 'supplier_deposit_pay_ids.state_invoice')
    def _get_residual(self):
        for i in self:
            amount_receipt = 0.0
            for bill in i.supplier_deposit_pay_ids:
                if bill.state_invoice in ['open', 'paid'] or bill.state_payment in ['post']:
                    amount_receipt += bill.amount_receipt
            amount_residual = i.amount_deposit - (amount_receipt)
            i.amount_residual = amount_residual

    po_id = fields.Many2one('purchase.order', string=u'PO', tracking=True, copy=False)
    name = fields.Char(string=u'เลขที่จ่ายมัดจำ', size=32, required=True, copy=False, tracking=True,
                       default='New')
    date = fields.Date(string=u'ลงวันที่', required=True, default=fields.Date.context_today, tracking=True)
    date_due = fields.Date(string=u'วันที่นัดจ่ายเงิน', required=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string=u'ผู้จำหน่าย', required=True, tracking=True)
    note = fields.Text(string=u'หมายเหตุ', tracking=True)
    line_ids = fields.One2many('ineco.supplier.deposit.line', 'payment_id', string=u'รายการจ่ายชำระ')
    other_ids = fields.One2many('ineco.supplier.deposit.other', 'payment_id', string=u'รายการอื่นๆ')
    amount_receipt = fields.Float(string=u'ยอดรับชำระ', compute='_get_receipts')
    change_number = fields.Boolean(string=u'เปลี่ยนเลขใบเสร็จ', )
    journal_id = fields.Many2one('account.journal', string=u'สมุดรายวันจ่าย', required=True, tracking=True)
    state = fields.Selection([('draft', 'Draft'), ('post', 'Posted'), ('cancel', 'Cancel')],
                             string=u'State', default='draft')
    amount_vat = fields.Float(string=u'ยอดภาษีมูลค่าเพิ่ม', tracking=True, compute='_get_vat', copy=False)
    amount_interest = fields.Float(string=u'ดอกเบี้ยจ่าย', tracking=True, copy=False)
    amount_cash = fields.Float(string=u'เงินสด', tracking=True, copy=False)
    amount_cheque = fields.Float(string=u'เช็คจ่าย', tracking=True, compute='_get_cheque', copy=False)
    amount_wht = fields.Float(string=u'ภาษีหัก ณ ที่จ่าย', tracking=True, compute='_get_wht',
                              copy=False)
    amount_discount = fields.Float(string=u'ส่วนลดรับ', tracking=True, copy=False)
    amount_paid = fields.Float(string=u'ยอดจ่ายชำระ', tracking=True, copy=False)
    amount_other = fields.Float(string=u'อื่นๆ', tracking=True, compute='_get_other', copy=False)
    cheque_ids = fields.One2many('ineco.cheque', 'supplier_deposit_id', string=u'เช็ครับ')
    vat_ids = fields.One2many('ineco.account.vat', 'supplier_deposit_id', string=u'ภาษีขาย')
    wht_ids = fields.One2many('ineco.wht', 'supplier_deposit_id', string=u'รายการภาษีหัก ณ ที่จ่าย')

    move_id = fields.Many2one('account.move', string=u'สมุดรายวัน', index=True, tracking=True)

    amount_residual = fields.Float(string=u'ยอดคงเหลือ',
                                   compute='_get_residual',
                                   # compute='_get_payment',
                                   store=True
                                   )
    is_amount_residual = fields.Boolean(u'ตัดหมด')
    payment_ids = fields.One2many('ineco.supplier.payment.deposit', 'name', string=u'ตัดมัดจำ')

    tax_type = fields.Selection(default='percent', string="ประเภทภาษี", required=True,
                                selection=[('percent', 'ภาษีแยก'), ('included', u'ภาษีรวม')])
    amount_type_tax = fields.Float(required=True, digits=(16, 0), default=7, string='อัตราภาษี')
    amount_deposit = fields.Float(string=u'ยอดรวมมัดจำ', compute='_get_receipts')
    journal_name = fields.Char(u'เปลี่ยนเลขเล่มเอกสาร')

    supplier_deposit_pay_ids = fields.One2many('ineco.supplier.payment.deposit', 'name',
                                               string=u'ประวัติการตัดตั้งหนี้')

    history_ids = fields.One2many('supplier.deposit.history.line', 'control_id', string=u'ประวัติการตัด')

    def up_deposit_cancel(self):
        if self.po_id:
            self.po_id.write({'deposit_id': False})

    def write(self, vals):
        res = super(InecoSupplierDeposit, self).write(vals)
        for line in self.line_ids:
            # line.test()
            amount = line.amount_untaxed

            ineco_account_vat_obj = self.env['ineco.account.vat']
            # print(self.line_ids)
            vat_data = {
                'supplier_deposit_id': self.id,
                'supplier_deposit_line_id': line.id,
                'name': self.name,
                'docdat': self.date,
                'partner_id': self.partner_id.id,
                'taxid': self.partner_id.vat or '',
                'depcod': self.partner_id.branch_no or '',
                'amount_untaxed': amount
            }
            ineco_account = self.env['ineco.account.vat'].search([('supplier_deposit_line_id', '=', line.id)])

            if not ineco_account:

                if self.tax_type == 'percent':
                    vat_data['amount_untaxed'] = amount
                    vat_data['amount_tax'] = amount * self.amount_type_tax / 100
                    ineco_account_vat_obj.create(vat_data)

                else:
                    vat_data['amount_untaxed'] = (amount * 100) / (100 + self.amount_type_tax)
                    vat_data['amount_tax'] = amount - (amount * 100) / (100 + self.amount_type_tax)
                    ineco_account_vat_obj.create(vat_data)

            ineco_update = self.env['ineco.account.vat'].search([
                ('supplier_deposit_line_id', '=', line.id),
                ('amount_untaxed', '!=', amount), ])

            if ineco_update:
                if self.tax_type == 'percent':
                    ineco_update.write({'amount_untaxed': amount})
                    ineco_update.write({'amount_tax': amount * self.amount_type_tax / 100})
                else:
                    ineco_update.write({'amount_untaxed': (amount * 100) / (100 + self.amount_type_tax)})
                    ineco_update.write({'amount_tax': amount - (amount * 100) / (100 + self.amount_type_tax)})
        return res

    def button_tax(self):
        amount = 0.0
        for line in self.line_ids:
            amount = line.amount_untaxed
            ineco_account_vat_obj = self.env['ineco.account.vat']
            # print(self.line_ids)
            vat_data = {
                'supplier_deposit_id': self.id,
                'name': self.name,
                'docdat': self.date,
                'partner_id': self.customer_id.id,
                'taxid': self.customer_id.vat or '',
                'depcod': self.customer_id.branch_no or '',
                'amount_untaxed': amount
            }
            if self.tax_type == 'percent':
                vat_data['amount_untaxed'] = amount
                vat_data['amount_tax'] = amount * self.amount_type_tax / 100
                ineco_account_vat_obj.create(vat_data)
            else:
                vat_data['amount_untaxed'] = (amount * 100) / (100 + self.amount_type_tax)
                vat_data['amount_tax'] = amount - (amount * 100) / (100 + self.amount_type_tax)
                ineco_account_vat_obj.create(vat_data)

    def button_post(self):
        if self.po_id:
            self.po_id.write({'deposit_id': self.id})
        self.ensure_one()
        if self.amount_receipt != self.amount_cheque + self.amount_wht + self.amount_cash + self.amount_discount + self.amount_other:
            raise UserError("ยอดไม่สมดุลย์")
        # if self.name == 'New':
        #     self.name = self.env['ir.sequence'].next_by_code('ineco.supplier.deposit')
        move = self.env['account.move']
        iml = []
        move_line = self.env['account.move.line']
        params = self.env['ir.config_parameter'].sudo()
        vat_sale_account_id = int(
            params.get_param('ineco_thai_account.vat_purchase_tax_break_account_id', default=False)) or False,
        if self.amount_vat:
            move_data_vals = {
                'partner_id': False,
                'debit': self.amount_vat,
                'credit': 0.0,
                'payment_id': False,
                'account_id': vat_sale_account_id,
            }
            iml.append((0, 0, move_data_vals))

        unearned_income_account_id = int(
            params.get_param('ineco_thai_account.unearned_expense_account_id', default=False)) or False,
        if unearned_income_account_id:
            move_data_vals = {
                'partner_id': self.partner_id.id,
                'debit': self.amount_receipt - self.amount_vat,
                'credit': 0.0,
                'payment_id': False,
                'account_id': unearned_income_account_id,
            }
            iml.append((0, 0, move_data_vals))
        cash_account_id = int(params.get_param('ineco_thai_account.cash_account_id', default=False)) or False,
        if self.amount_cash:
            move_data_vals = {
                'partner_id': False,
                'credit': self.amount_cash,
                'debit': 0.0,
                'payment_id': False,
                'account_id': cash_account_id,
            }
            iml.append((0, 0, move_data_vals))
        cheque_sale_account_id = int(
            params.get_param('ineco_thai_account.cheque_purchase_account_id', default=False)) or False,
        if self.amount_cheque:
            move_data_vals = {
                'partner_id': False,
                'credit': self.amount_cheque,
                'debit': 0.0,
                'payment_id': False,
                'account_id': cheque_sale_account_id,
            }
            iml.append((0, 0, move_data_vals))
        cash_discount_account_id = int(
            params.get_param('ineco_thai_account.cash_income_account_id', default=False)) or False,
        if self.amount_discount:
            move_data_vals = {
                'partner_id': False,
                'credit': self.amount_discount,
                'debit': 0.0,
                'payment_id': False,
                'account_id': cash_discount_account_id,
            }
            iml.append((0, 0, move_data_vals))
        wht_sale_account_id = int(
            params.get_param('ineco_thai_account.wht_purchase_account_id', default=False)) or False,
        if self.amount_wht:
            move_data_vals = {
                'partner_id': False,
                'credit': self.amount_wht,
                'debit': 0.0,
                'payment_id': False,
                'account_id': wht_sale_account_id,
            }
            iml.append((0, 0, move_data_vals))
        for other in self.other_ids:
            move_data_vals = {
                'partner_id': False,
                'debit': other.amount < 0 and abs(other.amount) or 0.0,
                'credit': other.amount > 0 and abs(other.amount) or 0.0,
                'payment_id': False,
                'account_id': other.name.id,
            }
            iml.append((0, 0, move_data_vals))
        self.state = 'post'
        move_vals = {
            'ref': self.name,
            'date': self.date,
            'company_id': self.env.user.company_id.id,
            'journal_id': self.journal_id.id,
            'partner_id': self.partner_id.id,
        }
        if self.move_id:
            self.move_id.write(move_vals)
            self.move_id.sudo().write({'line_ids': iml})
        else:
            new_move = move.create(move_vals)
            new_move.sudo().write({'line_ids': iml})
            # new_move.post()
            self.move_id = new_move
        self.move_id.post()
        ineco_update = self.env['ineco.account.vat'].search([('supplier_deposit_id', '=', self.id)])
        ineco_update.write({'name': self.name})
        self.write({'name': self.move_id.name})

        return True

    def button_cancel(self):
        if self.supplier_deposit_pay_ids:
            raise UserError("ไม่สามารถแก้ไข้ได้เนื่องจากตัดมัดจำไปแล้ว")

        self.ensure_one()
        self.move_id.button_cancel()
        self.up_deposit_cancel()
        self.state = 'cancel'
        return True

    def button_draft(self):
        self.ensure_one()
        for line in self.move_id:
            line.line_ids = False
        self.state = 'draft'
        return True

    # @api.model
    # def create(self, vals):
    #     vals['name'] = self.env['ir.sequence'].next_by_code('ineco.supplier.deposit')
    #     receipt_id = super(InecoSupplierDeposit, self.with_context(mail_create_nosubscribe=True)).create(vals)
    #     return receipt_id


class InecoSupplierDepositLine(models.Model):
    _name = 'ineco.supplier.deposit.line'
    _description = 'Supplier Deposit Line'

    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    # name = fields.Char(string=u'คำอธิบาย', required=True, index=True, copy=False, tracking=True)
    # amount_receipt = fields.Float(string=u'ยอดชำระ', copy=False, tracking=True)
    # payment_id = fields.Many2one('ineco.supplier.deposit', string=u'รับมัดจำ')

    name = fields.Char(string=u'คำอธิบาย', required=True, index=True, copy=False, tracking=True)
    amount_receipt = fields.Float(string=u'ยอดชำระ', copy=False, tracking=True)
    amount_untaxed = fields.Float(string='ยอดก่อนภาษี')
    amount_tax = fields.Float(string='ภาษี')
    # amount_total = fields.Float(string='ยอดเงินรวม')
    payment_id = fields.Many2one('ineco.supplier.deposit', string=u'รับมัดจำ')
    state = fields.Selection(string=u'State', related='payment_id.state', store=True)

    def button_trash(self):
        ineco_account = self.env['ineco.account.vat'].search([('supplier_deposit_line_id', '=', self.id), ])
        sql_ineco_account_vats = """
                        DELETE FROM ineco_account_vat
                        where id  =  %s
                         """ % (ineco_account.id)
        self._cr.execute(sql_ineco_account_vats)

        sql_line_ids = """
                                DELETE FROM ineco_supplier_deposit_line
                                where id  =  %s
                                 """ % (self.id)
        self._cr.execute(sql_line_ids)
        return True


class InecoSupplierDepositOther(models.Model):
    _name = 'ineco.supplier.deposit.other'
    _description = 'Supplier Deposit Other'

    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    name = fields.Many2one('account.account', string=u'ผังบัญชี', required=True, copy=False, index=True,
                           tracking=True)
    amount = fields.Float(string=u'จำนวนเงิน', copy=False, tracking=True)
    payment_id = fields.Many2one('ineco.supplier.deposit', string=u'รับมัดจำ')


class SupplierDepositHistoryLine(models.Model):
    _name = 'supplier.deposit.history.line'
    _description = 'History Deposit'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    name = fields.Char('Descriptions', tracking=True)
    control_id = fields.Many2one('ineco.supplier.deposit', string='Deposit')
    amount = fields.Float('Amount', digits=(16, 2), tracking=True)
    date_amount = fields.Datetime('Date Amount', tracking=True)
