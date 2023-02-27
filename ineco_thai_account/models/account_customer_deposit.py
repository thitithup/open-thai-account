# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class InecoCustomerDeposit(models.Model):
    _name = 'ineco.customer.deposit'
    _description = 'Customer Deposit'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = "id desc"

    @api.depends('line_ids')
    def _get_receipts(self):
        for receipt in self:
            receipt.amount_receipt = 0.0
            receipt.amount_deposit = 0.0
            total_receipt = 0.00
            total_deposit = 0.00
            for line in receipt.line_ids:
                untaxed = 0.0
                tax = 0.0
                total_deposit += line.amount_untaxed
                if receipt.tax_type == 'percent':
                    tax = line.amount_untaxed * receipt.amount_type_tax / 100
                    line.amount_tax = tax
                    line.amount_receipt = line.amount_untaxed + tax
                    total_receipt += line.amount_receipt
                else:
                    tax = line.amount_untaxed - (line.amount_untaxed * 100) / (100 + receipt.amount_type_tax)
                    line.amount_tax = tax
                    line.amount_receipt = line.amount_untaxed - tax
                    total_receipt += line.amount_untaxed
            receipt.amount_receipt = round(total_receipt, 2)
            receipt.amount_deposit = round(total_deposit, 2)

    #@api.multi
    @api.depends('wht_ids')
    def _get_wht(self):
        for receipt in self:
            receipt.amount_wht = 0.0
            for wht in receipt.wht_ids:
                receipt.amount_wht += wht.tax

    #@api.multi
    @api.depends('cheque_ids')
    def _get_cheque(self):
        for receipt in self:
            receipt.amount_cheque = 0.0
            for cheque in receipt.cheque_ids:
                receipt.amount_cheque += cheque.amount

    #@api.multi
    @api.depends('vat_ids')
    def _get_vat(self):
        for receipt in self:
            receipt.amount_vat = 0.0
            for vat in receipt.vat_ids:
                receipt.amount_vat += (vat.amount_tax / receipt.rate)

    #@api.multi
    @api.depends('other_ids')
    def _get_other(self):
        for receipt in self:
            receipt.amount_other = 0.0
            for vat in receipt.other_ids:
                receipt.amount_other += vat.amount

    #@api.multi
    @api.depends('amount_deposit')
    def _get_payment(self):
        for receipt in self:
            receipt.amount_residual = receipt.amount_deposit
            receipt_total = 0.0
            if receipt.payment_ids:
                for payment in receipt.payment_ids:
                    if payment.invoice_id and payment.invoice_id.state not in ('cancel'):
                        receipt_total += payment.amount_receipt
                    if payment.payment_id and payment.payment_id.state not in ('cancel'):
                        receipt_total += payment.amount_receipt
            receipt.amount_residual = receipt.amount_deposit - receipt_total
            if receipt.amount_residual:
                receipt.has_residual = True
            else:
                receipt.has_residual = False

    name = fields.Char(string=u'เลขที่ใบมัดจำ', size=32, required=True, copy=False, tracking=True,
                       default='New')
    date = fields.Date(string=u'ลงวันที่', required=True, default=fields.Date.context_today,
                       tracking=True)
    date_due = fields.Date(string=u'วันที่นัดรับเงิน', required=True, tracking=True)
    customer_id = fields.Many2one('res.partner', string=u'ลูกค้า', required=True, tracking=True)
    note = fields.Text(string=u'หมายเหตุ', tracking=True)
    line_ids = fields.One2many('ineco.customer.deposit.line', 'payment_id', string=u'รายการรับชำระ')
    other_ids = fields.One2many('ineco.customer.deposit.other', 'payment_id', string=u'อื่นๆ')
    amount_receipt = fields.Float(string=u'ยอดรับชำระ', compute='_get_receipts')
    change_number = fields.Boolean(string=u'เปลี่ยนเลขใบเสร็จ', )
    journal_id = fields.Many2one('account.journal', string=u'สมุดรายวันรับ', required=True, tracking=True)
    state = fields.Selection([('draft', 'Draft'), ('post', 'Posted'), ('cancel', 'Cancel')],
                             string=u'State', default='draft', tracking=True)
    amount_vat = fields.Float(string=u'ยอดภาษีมูลค่าเพิ่ม', tracking=True, compute='_get_vat', copy=False)
    amount_interest = fields.Float(string=u'ดอกเบี้ยรับ', tracking=True, copy=False)
    amount_cash = fields.Float(string=u'เงินสด', tracking=True, copy=False)
    amount_cheque = fields.Float(string=u'เช็ครับ', tracking=True, compute='_get_cheque', copy=False)
    amount_wht = fields.Float(string=u'ภาษีหัก ณ ที่จ่าย', tracking=True, compute='_get_wht',
                              copy=False)
    amount_discount = fields.Float(string=u'ส่วนลดเงินสด', tracking=True, copy=False)
    amount_paid = fields.Float(string=u'ยอดรับชำระ', tracking=True, copy=False)
    amount_other = fields.Float(string=u'อื่นๆ', tracking=True, compute='_get_other', copy=False)
    cheque_ids = fields.One2many('ineco.cheque', 'customer_deposit_id', string=u'เช็ครับ')
    vat_ids = fields.One2many('ineco.account.vat', 'customer_deposit_id', string=u'ภาษีขาย')
    wht_ids = fields.One2many('ineco.wht', 'customer_deposit_id', string=u'ภาษีหัก ณ ที่จ่าย')
    move_id = fields.Many2one('account.move', string=u'สมุดรายวัน', index=True)
    amount_residual = fields.Float(string=u'ยอดคงเหลือ', compute='_get_payment')  # store=True
    payment_ids = fields.One2many('ineco.customer.payment.deposit', 'name', string=u'ตัดมัดจำ')
    sale_order_id = fields.Many2one('sale.order', string='Sale Orders')
    tax_type = fields.Selection(default='percent', string="ประเภทภาษี", required=True,
                                selection=[('percent', 'ภาษีแยก'),
                                           ('included', u'ภาษีรวม')])
    amount_type_tax = fields.Float(required=True, digits=(16, 0), default=7)
    amount_deposit = fields.Float(string=u'ยอดรวมมัดจำ', compute='_get_receipts')
    journal_name = fields.Char(u'เปลี่ยนเลขเล่มเอกสาร', tracking=True)

    company_id = fields.Many2one('res.company', string='Company', store=True, readonly=True, change_default=True,
                                 default=lambda self: self.env.company)
    amount_residual = fields.Float(string=u'ยอดคงเหลือ', compute='_get_payment', store=True)  # store=True

    # 2022-10-10
    currency_id = fields.Many2one('res.currency', string='Currency', required=True,
                                  default=lambda self: self.env.user.company_id.currency_id.id)
    rate = fields.Float(string='Rate', digits=(12, 6), required=True, default=1.0)
    tax_id = fields.Many2one('account.tax', string='ภาษีมูลค่าเพิ่ม', required=True)
    no_tax_report = fields.Boolean(string='ไม่รวมรายงานภาษี', default=True)

    account_id = fields.Many2one('account.account', string='Credit Account', required=True,
                                 default=lambda self: self.company_id.unearned_income_account_id.id)
                                 # default=lambda self: int(self.env['ir.config_parameter'].get_param(
                                 #     'ineco_thai_account.unearned_income_account_id')))

    has_residual = fields.Boolean(string='Has Balance', compute='_get_payment', search='_search_residual')
    other_baht_ids = fields.One2many('ineco.customer.deposit.baht', 'payment_id', string='Other Baht')

    history_ids = fields.One2many('deposit.history.line', 'control_id', string=u'ประวัติการตัด')

    period_id = fields.Many2one('ineco.account.period', string='งวดบัญชี', compute='_compute_period', store=True,
                                readonly=True)

    type_deposit = fields.Selection([('in', u'รับ'), ('out', 'จ่าย')],
                                    string=u'type_deposit', tracking=True)

    # @api.depends('company_id')
    @api.onchange('company_id','customer_id')
    def _compute_account_id(self):
        for rec in self:
            rec.account_id = rec.company_id.unearned_income_account_id.id

    @api.depends("date")
    def _compute_period(self):
        for data in self:
            periods = self.env['ineco.account.period'].finds(dt=data.date)
            if periods:
                if len(periods) > 1:
                    data.period_id = periods[0]
                else:
                    data.period_id = periods



    #@api.multi
    def _search_residual(self, operator, value):
        all = []
        for data in self.search([]):
            if data.amount_residual > 0:
                all.append(data.id)
        return [('id', 'in', all)]

    @api.onchange('tax_id')
    def onchange_tax_id(self):
        if self.tax_id.price_include:
            self.tax_type = 'included'
        else:
            self.tax_type = 'percent'
        if self.tax_id.amount == 0.00:
            self.no_tax_report = True
        else:
            self.no_tax_report = False
        self.amount_type_tax = self.tax_id.amount

    #@api.multi
    def write(self, vals):
        res = super(InecoCustomerDeposit, self).write(vals)
        if not self.no_tax_report:
            for line in self.line_ids:
                # line.test()
                amount = line.amount_untaxed * self.rate

                ineco_account_vat_obj = self.env['ineco.account.vat']
                # print(self.line_ids)
                vat_data = {
                    'customer_deposit_id': self.id,
                    'customer_deposit_line_id': line.id,
                    'name': self.name,
                    'docdat': self.date,
                    'partner_id': self.customer_id.id,
                    'taxid': self.customer_id.vat or '',
                    'depcod': self.customer_id.branch_no or '',
                    'amount_untaxed': amount,

                }
                ineco_account = self.env['ineco.account.vat'].search([
                    ('customer_deposit_line_id', '=', line.id),
                ])

                if not ineco_account:

                    if self.tax_type == 'percent':
                        vat_data['amount_untaxed'] = amount
                        vat_data['amount_tax'] = (amount * self.amount_type_tax / 100)
                        ineco_account_vat_obj.create(vat_data)

                    else:
                        vat_data['amount_untaxed'] = ((amount * 100) / (100 + self.amount_type_tax))
                        vat_data['amount_tax'] = (amount - (amount * 100) / (100 + self.amount_type_tax))
                        ineco_account_vat_obj.create(vat_data)

                ineco_update = self.env['ineco.account.vat'].search([
                    ('customer_deposit_line_id', '=', line.id),
                    ('amount_untaxed', '!=', amount), ])

                if ineco_update:
                    if self.tax_type == 'percent':
                        ineco_update.write({'amount_untaxed': amount})
                        ineco_update.write({'amount_tax': amount * self.amount_type_tax / 100})
                    else:
                        ineco_update.write({'amount_untaxed': (amount * 100) / (100 + self.amount_type_tax)})
                        ineco_update.write({'amount_tax': amount - (amount * 100) / (100 + self.amount_type_tax)})
        return res

    #@api.multi
    def button_tax(self):
        amount = 0.0
        for line in self.line_ids:
            amount = line.amount_untaxed
            ineco_account_vat_obj = self.env['ineco.account.vat']
            # print(self.line_ids)
            vat_data = {
                'customer_deposit_id': self.id,
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

    #@api.multi
    def button_post(self):
        company_currency_id = self.env.user.company_id.currency_id.id
        if self.currency_id.id != company_currency_id:
            if self.rate == 1.00:
                raise UserError('เรทไม่ควรเป็น 1.00')
            if self.rate <= 0.00:
                raise UserError('เรทไม่ควรต่ำกว่า 0.00')
        elif self.currency_id.id == company_currency_id:
            if self.rate != 1.00:
                raise UserError('เรทต้องเป็น 1.00')
        self.ensure_one()
        if round(self.amount_receipt, 2) != round(
                self.amount_cheque + self.amount_wht + self.amount_cash + self.amount_discount + self.amount_other, 2):
            raise UserError("ยอดไม่สมดุลย์")
        if self.name == 'New':
            self.name = self.env['ir.sequence'].next_by_code('ineco.customer.deposit')

        # ตรวจสอบอื่นๆ สกุลบาท
        baht_debit = 0.00
        baht_credit = 0.00
        for other_baht in self.other_baht_ids:
            baht_credit += round(other_baht.credit, 2)
            baht_debit += round(other_baht.debit, 2)
        if baht_debit != baht_credit:
            raise UserError('ช่องอื่นๆ สกุลเงินบาท ไม่สมดุลย์')
        move = self.env['account.move']
        iml = []
        move_line = self.env['account.move.line']
        params = self.env['ir.config_parameter'].sudo()
        # vat_sale_account_id = int(params.get_param('ineco_thai_v11.vat_sale_account_id', default=False)) or False,
        vat_sale_account_id = self.env['account.tax.repartition.line'].search([('invoice_tax_id', '=',self.tax_id.id ),
                                                                                ('repartition_type','=','tax')], limit=1).account_id.id
        company = self.env['res.company'].search([('id', '=', self.company_id.id)])

            # self.tax_id.invoice_repartition_line_idsaccount_id.id
        if self.amount_vat:
            move_data_vals = {
                'partner_id': False,
                # 'invoice_id': False,
                'debit': 0.0,
                'credit': round(self.amount_vat, 2) * self.rate,
                'payment_id': False,
                'account_id': vat_sale_account_id,
                'currency_id': self.currency_id.id,
                'amount_currency': -round(self.amount_vat, 2),
                'amount_residual_currency': -round(self.amount_vat, 2) * self.rate,
            }
            print('1', move_data_vals)
            iml.append((0, 0, move_data_vals))
        # unearned_income_account_id = int(
        #     params.get_param('ineco_thai_v11.unearned_income_account_id', default=False)) or False,
        unearned_income_account_id = self.account_id.id
        # if unearned_income_account_id:
        #     move_data_vals = {
        #         'partner_id': self.customer_id.id,
        #         # 'invoice_id': False,
        #         'debit': 0.0,
        #         'credit': round((round(self.amount_receipt, 2) - round(self.amount_vat, 2)) * self.rate, 2),
        #         'payment_id': False,
        #         'account_id': unearned_income_account_id,
        #         'currency_id': self.currency_id.id,
        #         'amount_currency': -(round(self.amount_receipt, 2) - round(self.amount_vat, 2)),
        #         'amount_residual_currency': -(round(self.amount_receipt, 2) - round(self.amount_vat, 2)) * self.rate,
        #     }
        #     print('2', move_data_vals)
        #     iml.append((0, 0, move_data_vals))
        # cash_account_id = int(params.get_param('ineco_thai_v11.cash_account_id', default=False)) or False,
        # if self.amount_cash:
        #     move_data_vals = {
        #         'partner_id': False,
        #         # 'invoice_id': False,
        #         'credit': 0.0,
        #         'debit': round(self.amount_cash, 2) * self.rate,
        #         'payment_id': False,
        #         'account_id': cash_account_id,
        #         'currency_id': self.currency_id.id,
        #         'amount_currency': round(self.amount_cash, 2),
        #         'amount_residual_currency': round(self.amount_cash, 2) * self.rate,
        #     }
        #     print('3', move_data_vals)
        #     iml.append((0, 0, move_data_vals))
        # cheque_sale_account_id = int(params.get_param('ineco_thai_v11.cheque_sale_account_id', default=False)) or False,
        # if self.amount_cheque:
        #     move_data_vals = {
        #         'partner_id': False,
        #         # 'invoice_id': False,
        #         'credit': 0.0,
        #         'debit': round(self.amount_cheque, 2) * self.rate,
        #         'payment_id': False,
        #         'account_id': cheque_sale_account_id,
        #         'currency_id': self.currency_id.id,
        #         'amount_currency': round(self.amount_cheque, 2),
        #         'amount_residual_currency': round(self.amount_cheque, 2) * self.rate,
        #     }
        #     print('4', move_data_vals)
        #     iml.append((0, 0, move_data_vals))
        # cash_discount_account_id = int(
        #     params.get_param('ineco_thai_v11.cash_discount_account_id', default=False)) or False,
        # if self.amount_discount:
        #     move_data_vals = {
        #         'partner_id': False,
        #         # 'invoice_id': False,
        #         'credit': 0.0,
        #         'debit': round(self.amount_discount, 2) * self.rate,
        #         'payment_id': False,
        #         'account_id': cash_discount_account_id,
        #         'currency_id': self.currency_id.id,
        #         'amount_currency': round(self.amount_discount, 2),
        #         'amount_residual_currency': round(self.amount_discount, 2) * self.rate,
        #     }
        #     print('5', move_data_vals)
        #     iml.append((0, 0, move_data_vals))
        # wht_sale_account_id = int(params.get_param('ineco_thai_v11.wht_sale_account_id', default=False)) or False,
        # if self.amount_wht:
        #     move_data_vals = {
        #         'partner_id': False,
        #         # 'invoice_id': False,
        #         'credit': 0.0,
        #         'debit': round(self.amount_wht, 2) * self.rate,
        #         'payment_id': False,
        #         'account_id': wht_sale_account_id,
        #         'currency_id': self.currency_id.id,
        #         'amount_currency': round(self.amount_wht, 2),
        #         'amount_residual_currency': round(self.amount_wht, 2) * self.rate,
        #     }
        #     print('6', move_data_vals)
        #     iml.append((0, 0, move_data_vals))
        # for other in self.other_ids:
        #     move_data_vals = {
        #         'partner_id': False,
        #         # 'invoice_id': False,
        #         'debit': other.amount > 0 and abs(round(other.amount, 2)) * self.rate or 0.0,
        #         'credit': other.amount < 0 and abs(round(other.amount, 2)) * self.rate or 0.0,
        #         'payment_id': False,
        #         'account_id': other.name.id,
        #         'currency_id': self.currency_id.id,
        #         'amount_currency': other.amount < 0 and -abs(round(other.amount, 2)) or abs(round(other.amount, 2)),
        #         'amount_residual_currency': other.amount < 0 and -abs(round(other.amount, 2)) * self.rate or abs(
        #             round(other.amount, 2)) * self.rate,
        #     }
        #     print('7', move_data_vals)
        #     iml.append((0, 0, move_data_vals))
        # for other in self.other_baht_ids:
        #     move_data_vals = {
        #         'partner_id': False,
        #         # 'invoice_id': False,
        #         'debit': other.debit,
        #         'credit': other.credit,
        #         'payment_id': False,
        #         'account_id': other.name.id,
        #     }
        #     print('8', move_data_vals)
        #     iml.append((0, 0, move_data_vals))
        if unearned_income_account_id:
            move_data_vals = {
                'partner_id': self.customer_id.id,
                # 'invoice_id': False,
                'debit': 0.0,
                'credit': self.amount_receipt - self.amount_vat,
                'payment_id': False,
                'account_id': unearned_income_account_id,
            }
            print(2, move_data_vals)
            iml.append((0, 0, move_data_vals))
        cash_account_id = company.cash_account_id.id
        if self.amount_cash:
            move_data_vals = {
                'partner_id': False,
                # 'invoice_id': False,
                'credit': 0.0,
                'debit': self.amount_cash,
                'payment_id': False,
                'account_id': cash_account_id,
            }
            print(3, move_data_vals)
            iml.append((0, 0, move_data_vals))
        cheque_sale_account_id = company.cheque_sale_account_id.id
        if self.amount_cheque:
            move_data_vals = {
                'partner_id': False,
                # 'invoice_id': False,
                'credit': 0.0,
                'debit': self.amount_cheque,
                'payment_id': False,
                'account_id': cheque_sale_account_id,
            }
            print(4, move_data_vals)
            iml.append((0, 0, move_data_vals))
        cash_discount_account_id = company.cash_discount_account_id.id
        if self.amount_discount:
            move_data_vals = {
                'partner_id': False,
                # 'invoice_id': False,
                'credit': 0.0,
                'debit': self.amount_discount,
                'payment_id': False,
                'account_id': cash_discount_account_id,
            }
            print(5, move_data_vals)
            iml.append((0, 0, move_data_vals))
        wht_sale_account_id = company.wht_sale_account_id.id
        if self.amount_wht:
            move_data_vals = {
                'partner_id': False,
                # 'invoice_id': False,
                'credit': 0.0,
                'debit': self.amount_wht,
                'payment_id': False,
                'account_id': wht_sale_account_id,
            }
            print(6, move_data_vals)
            iml.append((0, 0, move_data_vals))
        for other in self.other_ids:
            move_data_vals = {
                'partner_id': False,
                # 'invoice_id': False,
                'debit': other.amount > 0 and abs(other.amount) or 0.0,
                'credit': other.amount < 0 and abs(other.amount) or 0.0,
                'payment_id': False,
                'account_id': other.name.id,
            }
            print(7, move_data_vals)
            iml.append((0, 0, move_data_vals))
        periods = self.env['ineco.account.period'].finds(dt=self.date)
        if not periods:
            raise ValidationError(('[POST] ยังไม่มีการระบุงวดบัญชีในระบบ1'))
        self.state = 'post'
        move_vals = {
            'ref': self.name,
            'date': self.date,
            'company_id': self.env.user.company_id.id,
            'journal_id': self.journal_id.id,
            'partner_id': self.customer_id.id,
            'rate': self.rate
        }
        new_move = move.create(move_vals)
        new_move.sudo().write({'line_ids': iml})
        new_move.post()
        self.move_id = new_move
        ineco_update = self.env['ineco.account.vat'].search([('customer_deposit_id', '=', self.id)])
        if ineco_update:
            ineco_update.write({'name': self.name})
        self.write({'name': self.move_id.name})
        return True


    def button_post2(self):
        # if self.po_id:
        #     self.po_id.write({'deposit_id': self.id})
        self.ensure_one()
        if self.amount_receipt != self.amount_cheque + self.amount_wht + self.amount_cash + self.amount_discount + self.amount_other:
            raise UserError("ยอดไม่สมดุลย์")
        # if self.name == 'New':
        #     self.name = self.env['ir.sequence'].next_by_code('ineco.supplier.deposit')
        move = self.env['account.move']
        iml = []
        move_line = self.env['account.move.line']
        company = self.env['res.company'].search([('id','=',self.company_id.id)])
        vat_sale_account_id = company.vat_purchase_tax_break_account_id.id
        if self.amount_vat:
            move_data_vals = {
                'partner_id': False,
                'debit': self.amount_vat,
                'credit': 0.0,
                'payment_id': False,
                'account_id': vat_sale_account_id,
            }
            #print(1,move_data_vals)
            iml.append((0, 0, move_data_vals))

        unearned_income_account_id = company.unearned_expense_account_id.id
        if unearned_income_account_id:
            move_data_vals = {
                'partner_id': self.customer_id.id,
                'debit': self.amount_receipt - self.amount_vat,
                'credit': 0.0,
                'payment_id': False,
                'account_id': unearned_income_account_id,
            }
            #print(2, move_data_vals)
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
            #print(3, move_data_vals)
            iml.append((0, 0, move_data_vals))
        cheque_sale_account_id= company.cheque_purchase_account_id.id
        if self.amount_cheque:
            move_data_vals = {
                'partner_id': False,
                'credit': self.amount_cheque,
                'debit': 0.0,
                'payment_id': False,
                'account_id': cheque_sale_account_id,
            }
            #print(4, move_data_vals)
            iml.append((0, 0, move_data_vals))
        cash_discount_account_id= company.cash_income_account_id.id
        if self.amount_discount:
            move_data_vals = {
                'partner_id': False,
                'credit': self.amount_discount,
                'debit': 0.0,
                'payment_id': False,
                'account_id': cash_discount_account_id,
            }
            #print(5, move_data_vals)
            iml.append((0, 0, move_data_vals))
        wht_sale_account_id= company.wht_purchase_account_id.id
        if self.amount_wht:
            move_data_vals = {
                'partner_id': False,
                'credit':self.amount_wht,
                'debit': 0.0,
                'payment_id': False,
                'account_id': wht_sale_account_id,
            }
            #print(6, move_data_vals)
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
        # self.state = 'post'
        periods = self.env['ineco.account.period'].finds(dt=self.date)
        if not periods:
            raise ValidationError(('[POST] ยังไม่มีการระบุงวดบัญชีในระบบ2'))
        move_vals = {
            'ref': self.name,
            'date': self.date,
            'company_id': self.env.company.id,
            'journal_id': self.journal_id.id,
            'partner_id': self.customer_id.id,
            'period_id': periods.id
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
        self.write({'name': self.move_id.name,'state':'post'})

        return True
    #@api.multi
    def button_cancel(self):
        self.ensure_one()
        self.move_id.sudo().button_cancel()
        self.state = 'cancel'
        sql = """
                delete from ineco_account_vat
                where customer_deposit_id = {}
            """.format(self.id)
        self.env.cr.execute(sql)
        return True

    #@api.multi
    def button_draft(self):
        self.ensure_one()
        self.move_id = False
        self.state = 'draft'
        return True

    #@api.multi
    def button_journal(self):
        if self.move_id:
            self.move_id.name = self.journal_name
        return True


# @api.model
# def create(self, vals):
#     vals['name'] = self.env['ir.sequence'].next_by_code('ineco.customer.deposit')
#     receipt_id = super(InecoCustomerDeposit, self.with_context(mail_create_nosubscribe=True)).create(vals)
#     return receipt_id


class InecoCustomerDepositLine(models.Model):
    _name = 'ineco.customer.deposit.line'
    _description = 'Customer Deposit Line'

    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    name = fields.Char(string=u'คำอธิบาย', required=True, index=True, copy=False, tracking=True)
    amount_receipt = fields.Float(string=u'ยอดชำระ', copy=False, tracking=True)
    amount_untaxed = fields.Float(string='ยอดก่อนภาษี')
    amount_tax = fields.Float(string='ภาษี')
    # amount_total = fields.Float(string='ยอดเงินรวม')
    payment_id = fields.Many2one('ineco.customer.deposit', string=u'รับมัดจำ')
    state = fields.Selection([('draft', 'Draft'), ('post', 'Posted'), ('cancel', 'Cancel')],
                             string=u'State', related='payment_id.state', store=True)

    #@api.multi
    def button_trash(self):
        ineco_account = self.env['ineco.account.vat'].search([('customer_deposit_line_id', '=', self.id), ])
        sql_ineco_account_vats = """
                        DELETE FROM ineco_account_vat
                        where id  =  %s
                         """ % (ineco_account.id)
        self._cr.execute(sql_ineco_account_vats)

        sql_line_ids = """
                                DELETE FROM ineco_customer_deposit_line
                                where id  =  %s
                                 """ % (self.id)
        self._cr.execute(sql_line_ids)
        return True


class InecoCustomerDepositOther(models.Model):
    _name = 'ineco.customer.deposit.other'
    _description = 'Customer Deposit Other'

    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    name = fields.Many2one('account.account', string=u'ผังบัญชี', required=True, copy=False, index=True,
                           tracking=True)
    amount = fields.Float(string=u'จำนวนเงิน', copy=False, compute='_compute_amount', store=True,
                          tracking=True)
    debit = fields.Float(string=u'เดบิต', copy=False, tracking=True)
    credit = fields.Float(string=u'เครดิต', copy=False, tracking=True)
    payment_id = fields.Many2one('ineco.customer.deposit', string=u'รับมัดจำ')

    #@api.multi
    @api.depends('debit', 'credit')
    def _compute_amount(self):
        for data in self:
            if data.debit > 0:
                data.amount = data.debit
            elif data.credit > 0:
                data.amount = -data.credit
            else:
                data.amount = 0.00

class DepositHistoryLine(models.Model):
    _name = 'deposit.history.line'
    _description = 'History Deposit'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    name = fields.Char('Descriptions', tracking=True)
    control_id = fields.Many2one('ineco.customer.deposit', string='Deposit')
    amount = fields.Float('Amount', digits=(16, 2), tracking=True)
    date_amount = fields.Datetime('Date Amount', tracking=True)

class InecoCustomerDepositOtherBaht(models.Model):
    _name = 'ineco.customer.deposit.baht'
    _description = 'Customer Deposit Baht'

    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    name = fields.Many2one('account.account', string=u'ผังบัญชี', required=True, copy=False, index=True,
                           tracking=True)
    debit = fields.Float(string=u'เดบิต', copy=False, tracking=True)
    credit = fields.Float(string=u'เครดิต', copy=False, tracking=True)
    payment_id = fields.Many2one('ineco.customer.deposit', string=u'รับมัดจำ')
