# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, exceptions, fields, models, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning


class InecoSupplierPayment(models.Model):
    _name = 'ineco.supplier.payment'
    _description = 'Supplier Payment'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    @api.depends('line_ids')
    def _get_receipts(self):
        for receipt in self:
            receipt.amount_receipt = 0.0
            for line in receipt.line_ids:
                receipt.amount_receipt += line.amount_receipt

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

    @api.depends('deposit_ids')
    def _get_deposit(self):
        for receipt in self:
            receipt.amount_deposit = 0.0
            for deposit in receipt.deposit_ids:
                receipt.amount_deposit += deposit.pay_amount_receipt

    @api.depends('other_ids')
    def _get_other(self):
        for receipt in self:
            receipt.amount_other = 0.0
            for vat in receipt.other_ids:
                receipt.amount_other += vat.amount

    @api.depends('amount_deposit', 'amount_wht', 'amount_vat', 'amount_discount', 'amount_other',
                 'amount_receipt'
                 )
    def _get_amount_paid(self):
        paid = 0.0
        for pay in self:
            self.amount_paid = pay.amount_receipt - (
                    pay.amount_deposit + pay.amount_wht + pay.amount_vat + pay.amount_discount + pay.amount_other)

    @api.depends('vat_ids')
    def _get_tax_break(self):
        for receipt in self:
            amount_tax = 0.0
            for iv in receipt.vat_ids:
                amount_tax += iv.amount_tax
            receipt.amount_tax_break = amount_tax

    name = fields.Char(string=u'เลขที่', size=32, required=True, copy=False, tracking=True,
                       default='New')
    date = fields.Date(string=u'ลงวันที่', required=True, default=fields.Date.context_today,
                       tracking=True)
    date_due = fields.Date(string=u'วันจ่ายเงิน', required=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string=u'ผู้จำหน่าย', required=True, tracking=True)
    note = fields.Text(string=u'หมายเหตุ', tracking=True)
    line_ids = fields.One2many('ineco.supplier.payment.line', 'payment_id', string=u'รายการจ่ายชำระ')
    other_ids = fields.One2many('ineco.supplier.payment.other', 'payment_id', string=u'รายการอื่นๆ')
    # deposit_ids = fields.One2many('ineco.supplier.payment.deposit', 'payment_id', string=u'มัดจำ')

    deposit_ids = fields.One2many('ineco.customer.payment.deposit', 'supplier_payment_id', string=u'มัดจำ')

    amount_receipt = fields.Float(string=u'ยอดรับชำระ', compute='_get_receipts')
    change_number = fields.Boolean(string=u'เปลี่ยนเลขเอกสาร', )
    journal_id = fields.Many2one('account.journal', string=u'สมุดรายวันจ่าย', required=True,
                                 tracking=True)
    type_vat = fields.Selection(string=u'ประเภทกิจกรรม', related='journal_id.type_vat', )
    state = fields.Selection([('draft', 'Draft'), ('post', 'Posted'), ('cancel', 'Cancel')],
                             string=u'State', default='draft', tracking=True)
    amount_deposit = fields.Float(string=u'ยอดมัดจำ', tracking=True, compute='_get_deposit', copy=False)
    amount_vat = fields.Float(string=u'ยอดภาษีมูลค่าเพิ่ม', tracking=True, compute='_get_vat', copy=False)
    amount_interest = fields.Float(string=u'ดอกเบี้ยจ่าย', tracking=True, copy=False)
    amount_cash = fields.Float(string=u'เงินสด', tracking=True, copy=False)
    amount_cheque = fields.Float(string=u'เช็คจ่าย', tracking=True, compute='_get_cheque', copy=False)
    amount_wht = fields.Float(string=u'ภาษีหัก ณ ที่จ่าย', tracking=True, compute='_get_wht',
                              copy=False)
    amount_discount = fields.Float(string=u'ส่วนลดรับ', tracking=True, copy=False)
    amount_paid = fields.Float(string=u'ยอดจ่ายชำระ', tracking=True, copy=False,
                               compute='_get_amount_paid', digits=(16, 2))
    amount_other = fields.Float(string=u'อื่นๆ', tracking=True, compute='_get_other', copy=False)
    cheque_ids = fields.One2many('ineco.cheque', 'supplier_payment_id', string=u'รายการเช็คจ่าย', copy=False)
    vat_ids = fields.One2many('ineco.account.vat', 'supplier_payment_id', string=u'ภาษีซื้อ', copy=False)
    wht_ids = fields.One2many('ineco.wht', 'supplier_payment_id', string=u'รายการภาษีหัก ณ ที่จ่าย', copy=False)

    move_id = fields.Many2one('account.move', string=u'สมุดรายวัน', index=True, copy=False, tracking=True)

    amount_tax_break = fields.Float(string=u'ยอดภาษีพัก', tracking=True, compute='_get_tax_break',
                                    copy=False)
    # Followers
    partner_ids = fields.Many2one('res.partner', string=u'ส่งเรื่องให้ผู้อนุมัติ')
    channel_ids = fields.Many2one('mail.channel', string='ส่งเข้ากลุ่มChat')
    expense = fields.Boolean(u'ชำระค่าใช้จ่าย',
                             related='journal_id.expense',
                             tracking=True,
                             store=True, readonly=True,
                             related_sudo=False
                             )
    company_id = fields.Many2one('res.company', string='Company', store=True, readonly=True, change_default=True,
                                 default=lambda self: self.env.company)

    account_id = fields.Many2one('account.account', string='Account',
                                 related='partner_id.property_account_payable_id',
                                 tracking=True)

    @api.onchange('partner_id', )
    def _onchange_partner_deposit(self):
        warning = {}
        deposits = self.env['ineco.supplier.deposit'].search([('partner_id', '=', self.partner_id.id),
                                                              ('amount_residual', '!=', 0.0)])
        note = []
        for de in deposits:
            message = f'เลขที่เอกสารมัดจำ {de.name} คงเหลือ {de.amount_residual} บาท '
            note.append(message)
        note2 = ''
        for n in note:
            note2 += n + '\n'
        if deposits:
            warning = {
                'title': _("มีเงินมัดจ่ายมัดจำ %s") % self.partner_id.name,
                'message': note2
            }
        res = {}
        if warning:
            res['warning'] = warning
        return res

    def button_get_iv(self):
        cumtomer_pay = self.env['ineco.supplier.payment.line']
        invoices = self.env['account.move'].search([
            ('partner_id', '=', self.partner_id.id),
            ('residual_signed', '!=', 0),
            ('state', 'not in', ('draft', 'cancel', 'paid')),
            ('type', 'in', ('in_invoice', 'in_refund')),
        ], order='id desc')
        for invoice in invoices:
            data = {
                'name': invoice.id,
                'user_id': invoice.user_id.id,
                'payment_id': self.id,
                'amount_total': invoice.amount_total_signed,
                'amount_residual': invoice.residual_signed,
                'amount_receipt': invoice.residual_signed
            }
            cumtomer_pay = self.env['ineco.supplier.payment.line'].search([
                ('name', '=', invoice.id), ('payment_id', '=', self.id)
            ])
            if not cumtomer_pay:
                cumtomer_pay.create(data)

    def button_post_tax(self):
        for pay in self.line_ids:
            pay.button_tax_break()

    def create_history_deposit(self):
        for line in self.deposit_ids:
            line.name.create_history(line.pay_amount_receipt, self.name)

    def button_post(self):
        self.add_follower_id()
        self.ensure_one()
        # รับชำระ+ดอกเบี้ยรับ = อื่นๆ +เงินสด+ภาษีหักถูก ณ ที่จ่าย+เช็ครับ+ส่วนลดเงินสด+ยอดมัดจำ
        # print(self.amount_receipt + self.amount_interest)
        # print(self.amount_deposit + self.amount_cheque + self.amount_wht + self.amount_cash + self.amount_discount + self.amount_other)
        # print(self.amount_deposit , self.amount_cheque , self.amount_wht , self.amount_cash , self.amount_discount , self.amount_other)

        if round(self.amount_receipt + self.amount_interest, 2) != round(
                self.amount_deposit + self.amount_cheque + self.amount_wht + self.amount_cash + self.amount_discount + self.amount_other,
                2):
            raise UserError("ยอดไม่สมดุลย์")
        move = self.env['account.move']
        iml = []
        move_line = self.env['account.move.line']
        company = self.env['res.company'].search([('id', '=', self.company_id.id)])

        # Credit Side
        vat_sale_account_id = company.vat_purchase_account_id.id
        vat_sale_break = self.env['account.account'].search([
            ('wait', '=', True),
            # ('active', '=', True)
        ], limit=1)

        if self.vat_ids:
            move_data_vals = {
                'partner_id': False,
                'debit': 0.0,
                'credit': self.amount_tax_break,
                'payment_id': False,
                'account_id': vat_sale_break.id,
            }
            # print('1',move_data_vals)
            iml.append((0, 0, move_data_vals))
        if self.amount_vat:
            move_data_vals = {
                'partner_id': False,
                'debit': self.amount_vat,
                'credit': 0.0,
                'payment_id': False,
                'account_id': vat_sale_account_id,
                # 'vat_ids': {}
            }
            # print('2', move_data_vals)
            iml.append((0, 0, move_data_vals))

        interest_income_account_id = company.interest_expense_account_id.id
        if self.amount_interest:
            move_data_vals = {
                'partner_id': False,
                'debit': self.amount_interest,
                'credit': 0.0,
                'payment_id': False,
                'account_id': interest_income_account_id,
            }
            # print('3', move_data_vals)
            iml.append((0, 0, move_data_vals))
        if self.expense:
            for ai in self.line_ids:
                receivable_account_id = ai.name.account_id.id
                pass
        else:
            receivable_account_id = self.partner_id.property_account_payable_id.id
        # #print(receivable_account_id)
        for ai in self.line_ids:
            move_data_vals = {
                'partner_id': self.partner_id.id,
                'debit': ai.amount_receipt > 0 and abs(ai.amount_receipt) or 0.0,
                'credit': ai.amount_receipt < 0 and abs(ai.amount_receipt) or 0.0,
                'payment_id': False,
                'account_id': ai.name.account_id.id,
                # 'account_id': receivable_account_id,
                'pay_id_thai': ai.name.id

            }
            # print('4', move_data_vals)
            iml.append((0, 0, move_data_vals))

        # Debit Side

        unearned_income_account_id = company.unearned_expense_account_id.id
        if self.amount_deposit:
            move_data_vals = {
                'partner_id': self.partner_id.id,
                'credit': self.amount_deposit,
                'debit': 0.0,
                'payment_id': False,
                'account_id': unearned_income_account_id,
            }
            # print('5', move_data_vals)
            iml.append((0, 0, move_data_vals))

        cash_account_id = company.cash_account_id.id
        if self.amount_cash:
            move_data_vals = {
                'partner_id': False,
                'credit': self.amount_cash,
                'debit': 0.0,
                'payment_id': False,
                'account_id': cash_account_id,
            }
            # print('6', move_data_vals)
            iml.append((0, 0, move_data_vals))
        cheque_sale_account_id = company.cheque_purchase_account_id.id
        if self.amount_cheque:
            move_data_vals = {
                'partner_id': False,
                'credit': self.amount_cheque,
                'debit': 0.0,
                'payment_id': False,
                'account_id': cheque_sale_account_id,
            }
            # print('7', move_data_vals)
            iml.append((0, 0, move_data_vals))
        cash_discount_account_id = company.cash_income_account_id.id
        if self.amount_discount:
            move_data_vals = {
                'partner_id': False,
                'credit': self.amount_discount,
                'debit': 0.0,
                'payment_id': False,
                'account_id': cash_discount_account_id,
            }
            # print('8', move_data_vals)
            iml.append((0, 0, move_data_vals))

        if self.partner_id.company_type is 'company':
            wht_sale_account_id = company.wht_purchase_account_id.id
        elif self.partner_id.company_type is 'person':
            wht_sale_account_id = company.wht_purchase_personal_account_id.id

        # wht_sale_account_id=int(params.get_param('ineco_thai_account.wht_purchase_account_id', default=False)) or False,
        if self.amount_wht:
            move_data_vals = {
                'partner_id': False,
                'credit': self.amount_wht,
                'debit': 0.0,
                'payment_id': False,
                'account_id': wht_sale_account_id,
            }
            # print('9', move_data_vals)
            iml.append((0, 0, move_data_vals))
        for other in self.other_ids:
            move_data_vals = {
                'partner_id': False,
                # 'invoice_id': False,
                'debit': other.amount < 0 and abs(other.amount) or 0.0,
                'credit': other.amount > 0 and abs(other.amount) or 0.0,
                'payment_id': False,
                'account_id': other.name.id,
            }
            # print('10', move_data_vals)
            iml.append((0, 0, move_data_vals))

        move_vals = {
            'ref': self.name,
            'date': self.date,
            'date_due': self.date_due,
            'company_id': self.env.user.company_id.id,
            'journal_id': self.journal_id.id,
            'partner_id': self.partner_id.id,

        }
        if not self.move_id:
            new_move = move.create(move_vals)
            if self.name != 'New':
                new_move.name = self.name
            new_move.sudo().write({'line_ids': iml})
            new_move.post()
            self.move_id = new_move
        else:
            self.move_id.button_cancel()
            self.move_id.line_ids = False
            self.move_id.sudo().write({'line_ids': iml})
            self.move_id.post()

        for ml in self.move_id.line_ids:
            mol_id = []
            for ai in self.line_ids:
                if ml.account_id.id == ai.name.account_id.id and ml.pay_id_thai.id == ai.name.id:
                    mol_id.append(ai.name.id)
            mol_id.append(ml.id)
            domain = [('id', 'in', mol_id)]
            move_lines = self.env['account.move.line'].search(domain)
            for line in move_lines:
                line.reconciled = False
            move_lines.reconcile()

        self.write({'name': self.move_id.name, 'state': 'post'})
        self.create_history_deposit()
        for vat in self.vat_ids:
            period_id = self.env['ineco.account.period'].finds(dt=self.date)
            move_line = self.env['account.move.line'].search([
                ('move_id', '=', self.move_id.id),
                ('account_id', '=', vat_sale_account_id)
            ])
            vat.write({'tax_purchase_wait_ok': False,
                       'move_line_id': move_line.id, 'tax_purchase_ok': True,
                       'vatprd': self.date,
                       'account_id': vat_sale_account_id,
                       'period_id': period_id.id
                       })
            vat.reconciliation_in.vatprd = self.date
        return True

    def delect_history_deposit(self):
        for line in self.deposit_ids:
            line.name.delete_history(self.name)

    def button_post_2(self):
        self.move_id.post()
        self.state = 'post'
        invoice_ids = []
        for ai in self.line_ids:
            invoice_ids.append(ai.name.id)
        domain = [('account_id', '=', self.partner_id.property_account_payable_id.id),
                  '|', ('invoice_id', 'in', invoice_ids), ('move_id', '=', self.move_id.id),
                  ('partner_id', '=', self.partner_id.id),
                  ('reconciled', '=', False), '|', ('amount_residual', '!=', 0.0),
                  ('amount_residual_currency', '!=', 0.0)]

        move_lines = self.env['account.move.line'].search(domain)
        move_lines.reconcile()

    def add_follower_id(self):
        Model = self.env['ineco.supplier.payment'].search([('id', '=', self.id)])
        ch_obj = self.env['mail.channel']
        ch = ch_obj.sudo().search([('name', 'ilike', 'อนุมัติจ่ายประจำวัน')
                                   ], limit=1)
        self.channel_ids = ch
        if self.partner_ids or ch and hasattr(Model, 'message_subscribe'):
            records = Model
            records.message_subscribe(self.partner_ids.ids, self.channel_ids.ids, force=False)
        return False

    def button_04_cancel(self):
        self.ensure_one()
        s = self.name.encode('utf-8')
        b = r'แจ้งเรื่อง ขออนุมัติจ่าย เลขที่ ' + self.name + " ผู้จำหน่าย " + self.partner_id.name + "  จำนวน " + \
            str(round(round(self.amount_receipt, 2) + round(self.amount_interest, 2), 2)) + " บาท"
        self.message_post(body=b, subject=s, subtype='mt_comment')

    def button_cancel(self):
        self.ensure_one()
        if self.move_id:
            for line in self.move_id.line_ids:
                line.pay_id_thai = False
            self.move_id.button_draft()
            self.move_id.button_cancel()
            # self.delect_history_deposit()
        for vat in self.vat_ids:
            vat.reconciliation_in.vatprd = False
            vat.unlink()
        self.delect_history_deposit()
        self.state = 'cancel'
        return True

    def button_draft(self):
        self.ensure_one()
        self.move_id.button_cancel()
        # self.move_id.unlink()
        self.move_id = False
        self.state = 'draft'
        for vat in self.vat_ids:
            vat.reconciliation_in.vatprd = False
            vat.unlink()
        return True

    @api.model
    def create(self, vals):
        receipt_id = super(InecoSupplierPayment, self.with_context(mail_create_nosubscribe=True)).create(vals)
        # receipt_id.button_get_iv()
        return receipt_id


class InecoSupplierPaymentDeposit(models.Model):
    _name = 'ineco.supplier.payment.deposit'
    _description = 'Supplier Payment Deposit'

    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    @api.onchange('name')
    def onchange_invoice_id(self):
        if self.name:
            self.amount_total = self.name.amount_receipt
            # self.amount_residual = self.name.amount_residual

    @api.onchange('amount_receipt', 'amount_residual')
    # @api.depends('deposit_ids')
    def onchange_amount_receipt(self):
        if self.amount_receipt > self.amount_residual:
            raise UserError("ตัดยอดเกิน")

    name = fields.Many2one('ineco.supplier.deposit', string=u'ใบมัดจำ', required=True, copy=False, index=True,
                           tracking=True)
    amount_total = fields.Float(string=u'ยอดตามบิล', copy=False, tracking=True)
    amount_residual = fields.Float(string=u'ยอดคงเหลือ', related='name.amount_residual',
                                   copy=False, tracking=True)
    amount_receipt = fields.Float(string=u'ยอดชำระ', copy=False, tracking=True)
    payment_id = fields.Many2one('ineco.supplier.payment', string=u'รับชำระ')
    invoice_id = fields.Many2one('account.move', string=u'ใบแจ้งหนี้/ใบกำกับภาษี')
    date_invoice = fields.Date(string=u'ลงวันที่', related='invoice_id.invoice_date')
    state_invoice = fields.Selection(string=u'สถานะ', related='invoice_id.state')

    state_payment = fields.Selection(string=u'สถานะจ่าย', related='payment_id.state')

    invoice_id = fields.Many2one('account.move', string=u'ใบแจ้งหนี้/ใบกำกับภาษี')
    move_line = fields.Many2one('account.move.line', string=u'Move line', ondelete="restrict")

    def update_deposit(self):
        params = self.env['ir.config_parameter'].sudo()
        tax = False
        quantity = -1
        account_id = int(params.get_param('ineco_thai_account.cash_income_account_id', default=False)) or False,

        if self.invoice_id.invoice_line_ids:
            if not self.invoice_id.invoice_line_ids[0].tax_ids:
                raise UserError('ยังไม่ได้ระบุการคิดภาษี')
            tax = [self.invoice_id.invoice_line_ids[0].tax_ids[0].id]

        for cut in self:
            data = {
                'move_id': self.invoice_id.id,
                'exclude_from_invoice_tab': False,
                'name': "หักมัดจำ {}".format(cut.name.name),
                'quantity': quantity,
                'account_id': account_id,
                'customer_deposit_ids': cut.name.id,
                'tax_ids': tax,
                # เพิ่มยอดเงินคงเหลือ
                # 'price_unit': cut.amount_residual,
                # 'debit': cut.amount_residual,
                # 'balance': cut.amount_residual,
                # 'amount_currency': cut.amount_residual,
            }
            aml = self.env['account.move.line'].create(data)
            cut.update({'move_line': aml.id})


class InecoSupplierPaymentLine(models.Model):
    _name = 'ineco.supplier.payment.line'
    _description = 'Supplier Payment Line'

    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    @api.onchange('name')
    def onchange_invoice_id(self):
        if self.name:
            if self.name.move_id.move_type == 'in_invoice':
                self.amount_total = abs(self.name.move_id.amount_total_signed)
                self.amount_residual = abs(self.name.amount_residual)
                self.amount_receipt = abs(self.name.amount_residual)
            elif self.name.move_id.move_type == 'in_refund':
                self.amount_total = - abs(self.name.move_id.amount_total_signed)
                self.amount_residual = - abs(self.name.amount_residual)
                self.amount_receipt = - abs(self.name.amount_residual)
            else:
                self.amount_total = abs(self.name.move_id.amount_total_signed)
                self.amount_residual = abs(self.name.amount_residual)
                self.amount_receipt = abs(self.name.amount_residual)

    @api.depends('name')
    def _get_tax_break(self):
        for iv in self:
            tax_break = 0.0
            for line in iv.name:
                iv.is_tax_break = line.tax_purchase_wait_ok

    name = fields.Many2one('account.move.line', string=u'เลขที่เอกสาร', required=True, copy=False, index=True,
                           domain="[('amount_residual','>',0.0)]",
                           tracking=True)
    reference = fields.Char(string=u'ใบแจ้งหนี้/ใบกำกับภาษี', related='name.move_id.ref', readonly=True)
    date_invoice = fields.Date(string=u'ลงวันที่', related='name.date', readonly=True)
    # billing_id = fields.Many2one('ineco.billing', string=u'เลขที่ใบวางบิล', related='name.billing_id', copy=False,
    #                             index=True, tracking=True, readonly=True)
    user_id = fields.Many2one('res.users', string=u'พนักงานขาย', index=True, tracking=True)
    tax_break = fields.Float(string=u'ภาษีพัก',
                             # compute="_get_tax_break", store=True,
                             copy=False, tracking=True)
    amount_total = fields.Float(string=u'ยอดตามบิล', copy=False, tracking=True)
    amount_residual = fields.Float(string=u'ยอดค้างชำระ', copy=False, tracking=True)
    amount_receipt = fields.Float(string=u'ยอดชำระ', copy=False, tracking=True)
    payment_id = fields.Many2one('ineco.supplier.payment', string=u'รับชำระ')
    is_tax_break = fields.Boolean(u'มีภาษีพัก',
                                  # compute='_get_tax_break',
                                  store=True,
                                  copy=False, tracking=True)
    state = fields.Selection(string=u'State', related='payment_id.state', store=True)

    def button_tax_break(self):
        for iv in self:
            tax_break = 0.0
            range_obj = self.env['ineco.account.period'].search([('date_start', '<=', iv.payment_id.date),
                                                                 ('date_finish', '>', iv.payment_id.date),
                                                                 ])
            if range_obj:
                period_id = range_obj.id
            else:
                period_id = False
            for line in iv.name.ineco_vat_ids:
                if not line.vatprd:
                    tax_break += line.amount_tax
                    data = {
                        'supplier_payment_id': iv.payment_id.id,
                        'invoice_id': iv.name.id,
                        'move_line_id': False,
                        'name': iv.name.reference or u'โปรดระบุ',
                        'period_id': period_id,
                        'docdat': line.docdat,
                        'vatprd': iv.payment_id.date,
                        'partner_id': line.partner_id.id,
                        'partner_name': line.partner_name,
                        'taxid': line.taxid,
                        'depcod': line.depcod or '00000',
                        'amount_untaxed': line.amount_untaxed,
                        'amount_tax': line.amount_tax,
                        'amount_total': line.amount_total,
                        'reconciliation_in': line.id,
                        'tax_sale_ok': False,
                        'tax_purchase_wait_ok': False,
                        'tax_purchase_ok': True,
                    }
                    new_move_id = line.copy(data)

            iv.tax_break = tax_break
            return True


class InecoSupplierPaymentOther(models.Model):
    _name = 'ineco.supplier.payment.other'
    _description = 'Supplier Payment Other'

    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    @api.depends('name', 'dr', 'cr')
    def _compute_amount(self):
        for line in self:
            dr = line.dr
            cr = line.cr
            line.amount = cr - dr

    name = fields.Many2one('account.account', string=u'ผังบัญชี', required=True, copy=False, index=True,
                           tracking=True)
    dr = fields.Float(string=u'Dr', copy=False, tracking=True)
    cr = fields.Float(string=u'Cr', copy=False, tracking=True)

    amount = fields.Float(string=u'จำนวนเงิน', copy=False, tracking=True,
                          compute="_compute_amount", store=True)
    payment_id = fields.Many2one('ineco.supplier.payment', string=u'จ่ายชำระ')
