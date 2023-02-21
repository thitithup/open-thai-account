# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class InecoCustomerPayment(models.Model):
    _name = 'ineco.customer.payment'
    _description = 'Customer Payment'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.depends('line_ids')
    def _get_receipts(self):
        for receipt in self:
            gl_receivable = 0.0
            clear_debtor = 0.0
            gl_difference = 0.0
            receipt.amount_receipt = 0.0
            for line in receipt.line_ids:
                receipt.amount_receipt += line.amount_receipt
                gl_receivable += line.gl_receivable
                clear_debtor += line.clear_debtor
                gl_difference += line.difference
            receipt.gl_receivable = gl_receivable
            receipt.clear_debtor = clear_debtor
            receipt.gl_difference = gl_difference

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
            receipt.amount_tax_break = receipt.amount_vat

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

    @api.depends('transfer_ids')
    def _get_transfer(self):
        for receipt in self:
            receipt.amount_transfer = 0.0
            for vat in receipt.transfer_ids:
                receipt.amount_transfer += vat.amount

    @api.depends('exchange_rate_ids')
    def _compute_profit_loss(self):
        dr = 0.0
        cr = 0.0
        for loss in self:
            for line in loss.exchange_rate_ids:
                dr += line.dr
                cr += line.cr
            loss.profit_loss = cr - dr

    @api.model
    def _get_default_journal(self):
        journal = self.env['account.journal'].search([('type', '=', 'receive')])
        return journal

    @api.model
    def _get_default_currency(self):
        ''' Get the default currency from either the journal, either the default journal's company. '''
        journal = self._get_default_journal()
        return journal.currency_id or journal.company_id.currency_id

    name = fields.Char(string=u'เลขที่ใบเสร็จ', size=32, required=True, copy=False, tracking=True,
                       default='New')
    name_iv = fields.Char(string=u'เลขที่ใบกำกับ', size=32, required=True, copy=False, tracking=True,
                          default='New')
    date = fields.Date(string=u'ลงวันที่', required=True, default=fields.Date.context_today,
                       tracking=True)
    date_due = fields.Date(string=u'วันที่รับเงิน', required=True, tracking=True)
    customer_id = fields.Many2one('res.partner', string=u'ลูกค้า', required=True, tracking=True)
    note = fields.Text(string=u'หมายเหตุ', tracking=True)
    line_ids = fields.One2many('ineco.customer.payment.line', 'payment_id', string=u'รายการรับชำระ')
    other_ids = fields.One2many('ineco.customer.payment.other', 'payment_id', string=u'รายการอื่นๆ')

    transfer_ids = fields.One2many('ineco.customer.payment.transfer', 'payment_id', string=u'รายการเงินโอน')

    deposit_ids = fields.One2many('ineco.customer.payment.deposit', 'payment_id', string=u'มัดจำ')

    exchange_rate_ids = fields.One2many('ineco.customer.payment.exchange.rate', 'payment_id',
                                        string=u'กำไรขาดทุนอัตราแลกเปี่ยน')

    amount_receipt = fields.Float(string=u'ยอดรับชำระ',
                                  compute='_get_receipts'
                                  )
    change_number = fields.Boolean(string=u'เปลี่ยนเลขใบเสร็จ', )
    journal_id = fields.Many2one('account.journal', string=u'สมุดรายวันรับ', required=True, tracking=True,
                                 default=_get_default_journal)
    foreign = fields.Boolean(u'ต่างประเทศ', related='journal_id.foreign', )
    type_vat = fields.Selection(string=u'ประเภทกิจกรรม', related='journal_id.type_vat', )
    state = fields.Selection([('draft', 'Draft'), ('post', 'Posted'), ('cancel', 'Cancel')],
                             string=u'State', default='draft')
    amount_deposit = fields.Float(string=u'ยอดมัดจำ', tracking=True,
                                  compute='_get_deposit',
                                  copy=False)
    amount_vat = fields.Float(string=u'ยอดภาษีมูลค่าเพิ่ม', tracking=True,
                              compute='_get_vat',
                              copy=False)
    amount_interest = fields.Float(string=u'ดอกเบี้ยรับ', tracking=True, copy=False)
    amount_cash = fields.Float(string=u'เงินสด', tracking=True, copy=False)
    amount_cheque = fields.Float(string=u'เช็ครับ', tracking=True,
                                 compute='_get_cheque',
                                 copy=False)
    amount_wht = fields.Float(string=u'ภาษีหัก ณ ที่จ่าย', tracking=True,
                              compute='_get_wht',
                              copy=False)
    amount_discount = fields.Float(string=u'ส่วนลดเงินสด', tracking=True, copy=False)
    amount_paid = fields.Float(string=u'ยอดจ่ายชำระ', tracking=True, copy=False)
    amount_other = fields.Float(string=u'อื่นๆ', tracking=True,
                                compute='_get_other',
                                copy=False)
    amount_transfer = fields.Float(string=u'เงินโอน', tracking=True,
                                   compute='_get_transfer',
                                   copy=False)

    get_paid = fields.Float(string=u'-รับเงินขาด', tracking=True, copy=False)
    get_overgrown = fields.Float(string=u'+รับเงินเกิน', tracking=True, copy=False)

    profit_loss = fields.Float(string=u'+,- กำไรขาดทุนอัตราแลกเปลี่ยน', tracking=True, copy=False,
                               compute="_compute_profit_loss",
                               store=True)
    fee = fields.Float(string=u'ค่าธรรมเนียม', tracking=True, copy=False)

    cheque_ids = fields.One2many('ineco.cheque', 'customer_payment_id', string=u'รายการเช็ครับ', copy=False)
    vat_ids = fields.One2many('ineco.account.vat', 'customer_payment_id', string=u'ภาษีขาย', copy=False)
    wht_ids = fields.One2many('ineco.wht', 'customer_payment_id', string=u'รายการภาษีหัก ณ ที่จ่าย', copy=False)

    move_id = fields.Many2one('account.move', string=u'สมุดรายวัน', index=True, copy=False, tracking=True)

    amount_tax_break = fields.Float(string=u'ยอดภาษีพัก', tracking=True,
                                    compute='_get_vat',
                                    copy=False)

    gl_receivable = fields.Float(string=u'GLลูกหนี้', copy=False, tracking=True,
                                 compute='_get_receipts'
                                 )
    clear_debtor = fields.Float(string=u'ล้างลูกหนี้', copy=False, tracking=True,
                                compute='_get_receipts'
                                )
    gl_difference = fields.Float(string=u'ส่วนต่าง', copy=False, tracking=True,
                                 compute='_get_receipts'
                                 )

    company_id = fields.Many2one(string='Company', store=True, readonly=True,
                                 related='journal_id.company_id', change_default=True,
                                 default=lambda self: self.env.company)
    company_currency_id = fields.Many2one(string='Company Currency', readonly=True,
                                          related='journal_id.company_id.currency_id')
    currency_id = fields.Many2one('res.currency', store=True, readonly=True, tracking=True, required=False,
                                  states={'draft': [('readonly', False)]},
                                  string='Currency',
                                  default=_get_default_currency)
    rate = fields.Float(digits=(12, 4), default=1.0, help='The rate of the currency to the currency of rate 1',
                        tracking=True)

    company_id = fields.Many2one('res.company', string='Company', store=True, readonly=True, change_default=True,
                                 default=lambda self: self.env.company)

    account_id = fields.Many2one('account.account', string='Account',
                                 related='customer_id.property_account_receivable_id',
                                 tracking=True)

    def get_currency_rates(self):
        if self.date_due:
            currency_rates = self.currency_id._get_rates(self.company_id, self.date_due)
            rate = currency_rates.get(self.currency_id.id)
            self.rate = rate
        # self.update({'rate': rate})

    @api.onchange('currency_id', 'date_due')
    def _onchange_currency_id(self):
        rate_obj = self.env['res.currency.rate']
        if self.currency_id.id == self.company_id.currency_id.id:
            self.rate = 1.0
        else:
            rate = rate_obj.search([
                ('currency_id', '=', self.currency_id.id),
                ('name', '=', self.date_due),
            ])
            if not rate:
                res = {}
                res['warning'] = {
                    'title': ("มีเงินมัดจ่ายมัดจำ"),
                    'message': 'ค้นหาค่าเงินไม่เจอกรุณาระบุ'
                }
                self.update({'rate': 0.0})
                self.rate = 0.0
                return res
            else:
                currency_rates = self.currency_id._get_rates(self.company_id, self.date_due)
                rate = currency_rates.get(self.currency_id.id)
                self.update({'rate': rate})

    def button_get_iv(self):
        self.get_currency_rates()
        cumtomer_pay = self.env['ineco.customer.payment.line']
        invoices = self.env['account.move'].search([
            ('partner_id', '=', self.customer_id.id),
            ('residual_signed', '!=', 0),
            ('state', 'not in', ('draft', 'cancel', 'paid')),
            ('type', 'in', ('out_invoice', 'out_refund')),
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
            cumtomer_pay = self.env['ineco.customer.payment.line'].search([
                ('name', '=', invoice.id), ('payment_id', '=', self.id)
            ])
            if not cumtomer_pay:
                cumtomer_pay.create(data)

    def check_deposit(self):
        for de in self.deposit_ids:
            if de.amount_residual < de.amount_receipt:
                raise UserError(f'รายการมัดจำยอดชำระมากกว่ายอดคงเหลือ เลขที่{de.name}')
            if de.amount_residual <= 0.0:
                raise UserError(f'รายการมัดจำถูกต้องใช้ไป หมดแล้ว เลขที่{de.name}')

    def create_history_deposit(self):
        for line in self.deposit_ids:
            line.name.create_history(line.pay_amount_receipt, self.name)

    def post_thai(self):
        self.ensure_one()
        # self.check_deposit()
        # รับชำระ+ดอกเบี้ยรับ = อื่นๆ +เงินสด+ภาษีหักถูก ณ ที่จ่าย+เช็ครับ+ส่วนลดเงินสด+ยอดมัดจำ
        if round(self.amount_receipt + self.amount_interest, 2) != round(
                self.amount_deposit + self.amount_cheque + self.amount_wht + self.amount_cash + self.amount_discount + self.amount_other + self.amount_transfer,
                2):
            raise UserError("ยอดไม่สมดุลย์")
        move = self.env['account.move']
        iml = []
        move_line = self.env['account.move.line']
        company = self.env['res.company'].search([('id', '=', self.company_id.id)])

        # Credit Side
        vat_sale_account_id = company.vat_sale_account_id.id
        vat_sale_tax_break_account_id = company.vat_sale_tax_break_account_id.id
        # กลับภาษีพัก

        if self.amount_tax_break:
            move_data_vals = {
                'partner_id': False,
                'debit': self.amount_tax_break,
                'credit': 0.0,
                'payment_id': False,
                'account_id': vat_sale_tax_break_account_id,
            }
            # print('1', move_data_vals)

            iml.append((0, 0, move_data_vals))
        for vat in self.vat_ids:
            move_data_vals = {
                'partner_id': False,
                'debit': 0.0,
                'credit': vat.amount_tax,
                'payment_id': False,
                'account_id': vat_sale_account_id,
            }
            # print('2',move_data_vals)
            iml.append((0, 0, move_data_vals))
        ## กลับภาษีพัก

        interest_income_account_id = company.interest_income_account_id.id
        if self.amount_interest:
            move_data_vals = {
                'partner_id': False,
                'debit': 0.0,
                'credit': self.amount_interest,
                'payment_id': False,
                'account_id': interest_income_account_id,
            }
            # print('3', move_data_vals)
            iml.append((0, 0, move_data_vals))
        # receivable_account_id = self.customer_id.property_account_receivable_id.id
        for ai in self.line_ids:
            move_data_vals = {
                'partner_id': self.customer_id.id,
                'debit': ai.amount_receipt < 0 and abs(ai.amount_receipt) or 0.0,
                'credit': ai.amount_receipt > 0 and abs(ai.amount_receipt) or 0.0,
                'payment_id': False,
                # 'account_id': receivable_account_id,
                'account_id': ai.name.account_id.id,
                'pay_id_thai': ai.name.id
            }
            # print('4', move_data_vals)
            iml.append((0, 0, move_data_vals))

        # Debit Side

        unearned_income_account_id = company.unearned_income_account_id.id
        if self.amount_deposit:
            move_data_vals = {
                'partner_id': self.customer_id.id,
                'credit': 0.0,
                'debit': self.amount_deposit,
                'payment_id': False,
                'account_id': unearned_income_account_id,
            }
            # print('5', move_data_vals)
            iml.append((0, 0, move_data_vals))

        cash_account_id = company.cash_account_id.id
        # print(cash_account_id)

        if self.amount_cash:
            move_data_vals = {
                'partner_id': False,
                'credit': 0.0,
                'debit': self.amount_cash,
                'payment_id': False,
                'account_id': cash_account_id,
            }
            # print('6', move_data_vals)
            iml.append((0, 0, move_data_vals))
        cheque_sale_account_id = company.cheque_sale_account_id.id
        if self.amount_cheque:
            move_data_vals = {
                'partner_id': False,
                'credit': 0.0,
                'debit': self.amount_cheque,
                'payment_id': False,
                'account_id': cheque_sale_account_id,
            }
            # print('7', move_data_vals)
            iml.append((0, 0, move_data_vals))
        cash_discount_account_id = company.cash_discount_account_id.id
        if self.amount_discount:
            move_data_vals = {
                'partner_id': False,
                'credit': 0.0,
                'debit': self.amount_discount,
                'payment_id': False,
                'account_id': cash_discount_account_id,
            }
            # print('8', move_data_vals)
            iml.append((0, 0, move_data_vals))
        wht_sale_account_id = company.wht_sale_account_id.id
        if self.amount_wht:
            move_data_vals = {
                'partner_id': False,
                'credit': 0.0,
                'debit': self.amount_wht,
                'payment_id': False,
                'account_id': wht_sale_account_id,
            }
            # print('9', move_data_vals)
            iml.append((0, 0, move_data_vals))

        for other in self.other_ids:
            move_data_vals = {
                'partner_id': False,
                'debit': other.amount > 0 and abs(other.amount) or 0.0,
                'credit': other.amount < 0 and abs(other.amount) or 0.0,
                'payment_id': False,
                'account_id': other.name.id,
            }
            # print('10', move_data_vals)
            iml.append((0, 0, move_data_vals))

        for transfer in self.transfer_ids:
            move_data_vals = {
                'partner_id': False,
                'debit': transfer.amount > 0 and abs(transfer.amount) or 0.0,
                'credit': transfer.amount < 0 and abs(transfer.amount) or 0.0,
                'payment_id': False,
                'account_id': transfer.name.id,
            }
            # print('11', move_data_vals)
            iml.append((0, 0, move_data_vals))

        # self.state = 'post'
        periods = self.env['ineco.account.period'].finds(dt=self.date)
        if not periods:
            raise ValidationError(_('[POST] ยังไม่มีการระบุงวดบัญชีในระบบ'))
        move_vals = {
            'ref': self.name,
            'date': self.date,
            'date_due': self.date_due,
            'company_id': self.env.company.id,
            'journal_id': self.journal_id.id,
            'partner_id': self.customer_id.id,
            'period_id': periods.id

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
        # for ai in self.line_ids:
        #     domain = [('account_id', '=', self.customer_id.property_account_receivable_id.id),
        #               '|', ('pay_id_thai', '=', ai.name.id),
        #               ('id', '=', ai.name.id),
        #               ('partner_id', '=', self.customer_id.id),
        #               ]
        #     move_lines = self.env['account.move.line'].search(domain)
        #     for line in move_lines:
        #         line.reconciled = False
        #     move_lines.reconcile()


        #หาคู่ในการ reconcile ของการรับเงิน จาก invoice
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

        # for ai in self.line_ids:
        #     if self.move_id:
        #         for ml in self.move_id.line_ids:
        #             if ml.account_id.id == ai.name.account_id.id:
        #                 mol_id.append(ml.id)
        #     mol_id.append(ai.name.id)
        # domain = [('id', 'in', mol_id)]
        #
        # move_lines = self.env['account.move.line'].search(domain)
        # for line in move_lines:
        #     line.reconciled = False
        # move_lines.reconcile()

        self.write({'name': self.move_id.name, 'state': 'post'})
        for line in self.line_ids:
            line.UpDateDone()
        self.create_history_deposit()
        for vat in self.vat_ids:
            move_line = self.env['account.move.line'].search([
                ('move_id', '=', self.move_id.id),
                ('account_id', '=', vat_sale_account_id)])
            for line in move_lines:
                vat.write({'tax_sale_wait_ok': False,
                           'move_line_id': line.id,
                           'tax_sale_ok': True,
                           'vatprd': self.date,
                           'account_id': vat_sale_account_id
                           })
                vat.reconciliation_in.vatprd = self.date
        return True

    # def post_foreign(self):
    #     currency_id = self.currency_id.id
    #     move = self.env['account.move']
    #     iml = []
    #     move_line = self.env['account.move.line']
    #     params = self.env['ir.config_parameter'].sudo()
    #
    #     # if self.profit_loss != self.gl_difference:
    #     #     raise UserError(f'กำไรขาดทุนจากอัตราแลกเปลี่ยนไม่สมดุล')
    #
    #     # Credit Side
    #     vat_sale_account_id = int(params.get_param('ineco_thai_account.vat_sale_account_id', default=False)) or False
    #     vat_sale_break_account_id = int(params.get_param('ineco_thai_account.vat_sale_tax_break_account_id', default=False)) or False
    #     ## กลับภาษีพัก
    #     vat_sale_break = self.env['account.tax'].search([
    #         ('tax_break', '=', True), ('type_tax_use', '=', 'sale'),
    #         ('active', '=', True)
    #     ])
    #     if self.amount_tax_break:
    #         move_data_vals = {
    #             'partner_id': False,
    #             'debit': round(self.amount_tax_break, 2),
    #             'credit': 0.0,
    #             'payment_id': False,
    #             'account_id': vat_sale_break_account_id,
    #             'currency_id': currency_id
    #         }
    #         # #print('move_data_vals1',move_data_vals)
    #
    #         iml.append((0, 0, move_data_vals))
    #     for vat in self.vat_ids:
    #         move_data_vals = {
    #             'partner_id': False,
    #             'debit': 0.0,
    #             'credit': round(vat.amount_tax, 2),
    #             'payment_id': False,
    #             'account_id': vat_sale_account_id,
    #             'currency_id': currency_id
    #         }
    #         # #print('move_data_vals2', move_data_vals)
    #         iml.append((0, 0, move_data_vals))
    #     ## กลับภาษีพัก
    #
    #     interest_income_account_id = int(
    #         params.get_param('ineco_thai_account.interest_income_account_id', default=False)) or False,
    #     if self.amount_interest:
    #         move_data_vals = {
    #             'partner_id': False,
    #             'debit': 0.0,
    #             'credit': round(self.amount_interest, 2),
    #             'payment_id': False,
    #             'account_id': interest_income_account_id,
    #             'currency_id': currency_id
    #         }
    #         # #print('move_data_vals3', move_data_vals)
    #         iml.append((0, 0, move_data_vals))
    #     receivable_account_id = self.customer_id.property_account_receivable_id.id
    #     for ai in self.line_ids:
    #         move_data_vals = {
    #             'partner_id': self.customer_id.id,
    #             'pay_id_thai': ai.name.id,
    #             'debit': ai.clear_debtor < 0 and round(abs(ai.clear_debtor), 2) or 0.0,
    #             'credit': ai.clear_debtor > 0 and round(abs(ai.clear_debtor), 2) or 0.0,
    #             'payment_id': False,
    #             'account_id': receivable_account_id,
    #             'foreign': True,
    #             'foreign_receivable': ai.amount_receipt,
    #             'currency_id': currency_id,
    #         }
    #         # #print('move_data_vals4', move_data_vals)
    #         iml.append((0, 0, move_data_vals))
    #
    #     # Debit Side
    #
    #     unearned_income_account_id = int(
    #         params.get_param('ineco_thai_account.unearned_income_account_id', default=False)) or False,
    #     if self.amount_deposit:
    #         move_data_vals = {
    #             'partner_id': self.customer_id.id,
    #             'credit': 0.0,
    #             'debit': round(self.amount_deposit, 2),
    #             'payment_id': False,
    #             'account_id': unearned_income_account_id,
    #             'currency_id': currency_id
    #         }
    #         # #print('move_data_vals5', move_data_vals)
    #         iml.append((0, 0, move_data_vals))
    #
    #     cash_account_id = int(params.get_param('ineco_thai_account.cash_account_id', default=False)) or False,
    #     if self.amount_cash:
    #         move_data_vals = {
    #             'partner_id': False,
    #             'credit': 0.0,
    #             'debit': round((self.amount_cash * self.rate), 2),
    #             'payment_id': False,
    #             'account_id': cash_account_id,
    #             'currency_id': currency_id
    #         }
    #         # #print('move_data_vals6', move_data_vals)
    #         iml.append((0, 0, move_data_vals))
    #     cheque_sale_account_id = int(
    #         params.get_param('ineco_thai_account.cheque_sale_account_id', default=False)) or False,
    #     if self.amount_cheque:
    #         move_data_vals = {
    #             'partner_id': False,
    #             'credit': 0.0,
    #             'debit': round(self.amount_cheque, 2),
    #             'payment_id': False,
    #             'account_id': cheque_sale_account_id,
    #             'currency_id': currency_id
    #         }
    #         # #print('move_data_vals7', move_data_vals)
    #         iml.append((0, 0, move_data_vals))
    #     cash_discount_account_id = int(
    #         params.get_param('ineco_thai_account.cash_discount_account_id', default=False)) or False,
    #     if self.amount_discount:
    #         move_data_vals = {
    #             'partner_id': False,
    #             'credit': 0.0,
    #             'debit': round(self.amount_discount, 2),
    #             'payment_id': False,
    #             'account_id': cash_discount_account_id,
    #             'currency_id': currency_id
    #         }
    #         # #print('move_data_vals8', move_data_vals)
    #         iml.append((0, 0, move_data_vals))
    #     wht_sale_account_id = int(params.get_param('ineco_thai_account.wht_sale_account_id', default=False)) or False,
    #     if self.amount_wht:
    #         move_data_vals = {
    #             'partner_id': False,
    #             'credit': 0.0,
    #             'debit': round(self.amount_wht, 2),
    #             'payment_id': False,
    #             'account_id': wht_sale_account_id,
    #             'currency_id': currency_id
    #         }
    #         # #print('move_data_vals9', move_data_vals)
    #         iml.append((0, 0, move_data_vals))
    #     for other in self.other_ids:
    #         move_data_vals = {
    #             'partner_id': False,
    #             'debit': other.amount > 0 and round(abs(other.amount), 2) or 0.0,
    #             'credit': other.amount < 0 and round(abs(other.amount), 2) or 0.0,
    #             'payment_id': False,
    #             'account_id': other.name.id,
    #             'currency_id': currency_id
    #         }
    #         # #print('move_data_vals10', move_data_vals)
    #         iml.append((0, 0, move_data_vals))
    #
    #     for transfer in self.transfer_ids:
    #         move_data_vals = {
    #             'partner_id': False,
    #             'debit': transfer.amount > 0 and round(abs(transfer.amount), 2) or 0.0,
    #             'credit': transfer.amount < 0 and round(abs(transfer.amount), 2) or 0.0,
    #             'payment_id': False,
    #             'account_id': transfer.name.id,
    #             'currency_id': currency_id
    #         }
    #         # #print('move_data_vals11', move_data_vals)
    #         iml.append((0, 0, move_data_vals))
    #     for exchange in self.exchange_rate_ids:
    #         move_data_vals = {
    #             'partner_id': False,
    #             'debit': round(exchange.dr, 2),
    #             'credit': round(exchange.cr, 2),
    #             'payment_id': False,
    #             'account_id': exchange.name.id,
    #             'currency_id': currency_id
    #         }
    #         # #print('move_data_vals11', move_data_vals)
    #         iml.append((0, 0, move_data_vals))
    #     self.state = 'post'
    #     move_vals = {
    #         'date': self.date,
    #         'date_due': self.date_due,
    #         'company_id': self.env.user.company_id.id,
    #         'journal_id': self.journal_id.id,
    #         'partner_id': self.customer_id.id,
    #         'currency_id': self.currency_id.id,
    #         'rate': self.rate
    #     }
    #     if not self.move_id:
    #         new_move = move.create(move_vals)
    #         if self.name != 'New':
    #             new_move.name = self.name
    #         new_move.sudo().write({'line_ids': iml})
    #         new_move.post()
    #         self.move_id = new_move
    #     else:
    #         self.move_id.line_ids = False
    #         self.move_id.sudo().write({'line_ids': iml})
    #         self.move_id.post()
    #
    #     for ai in self.line_ids:
    #         moves = []
    #         moves = [new_move.id,ai.name.id]
    #         domain = [('account_id', '=', self.customer_id.property_account_receivable_id.id),
    #                   ('move_id', 'in', moves),
    #                   ('parent_state', '=', 'posted'),
    #                   ('reconciled', '=', False),
    #                   ]
    #         move_lines = self.env['account.move.line'].search(domain)
    #         move_lines.reconcile()
    #     self.write({'name': self.move_id.name})
    #     for line in self.line_ids:
    #         line.UpDateDone()
    #     self.create_history_deposit()
    #
    #     return True

    def button_post(self):
        # if self.vat_ids:
        self.button_post_tax()
        if self.foreign == False:
            self.post_thai()
        if self.foreign == True:
            self.post_foreign()

    def button_cancel(self):
        self.ensure_one()
        if self.move_id:
            for line in self.move_id.line_ids:
                line.pay_id_thai = False
            self.move_id.button_draft()
            self.move_id.button_cancel()
            self.delect_history_deposit()
        for vat in self.vat_ids:
            vat.unlink()
        self.state = 'cancel'
        return True

    def delect_history_deposit(self):
        for line in self.deposit_ids:
            line.name.delete_history(self.name)

    def button_draft(self):
        self.ensure_one()
        self.move_id.button_cancel()
        # self.move_id.unlink()
        self.move_id = False
        self.state = 'draft'
        return True

    @api.model
    def create(self, vals):
        receipt_id = super(InecoCustomerPayment, self.with_context(mail_create_nosubscribe=True)).create(vals)
        return receipt_id

    def button_post_tax(self):
        for pay in self.line_ids:
            ineco_account_vat_obj = self.env['ineco.account.vat'].search([
                ('invoice_id', '=', pay.name.move_id.id),
                ('move_line_id', '!=', False),
                ('tax_sale_wait_ok', '=', True)
            ])
            if not pay.name.ineco_iv:
                pay.name.ineco_iv = self.env['ir.sequence'].next_by_code('ineco.customer.payment.iv')
            for vat_obj in ineco_account_vat_obj:
                period_id = self.env['ineco.account.period'].finds(dt=self.date)
                vat_type = 'purchase'
                vat = self.env['ineco.account.vat'].search([
                    ('customer_payment_id', '=', self.id), ('invoice_id', '=', pay.name.move_id.id),
                    ('name', '=', self.name_iv)])

                if not vat:
                    vat_obj.copy({
                        'docdat': self.date,
                        'name': pay.name.ineco_iv,
                        'period_id': period_id.id,
                        'customer_payment_id': self.id,
                        'account_id': False,
                        'move_line_id': False,
                        'reconciliation_in': vat_obj.id
                    })


class InecoCustomerPaymentDeposit(models.Model):
    _name = 'ineco.customer.payment.deposit'
    _description = 'Customer Payment Deposit'

    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.onchange('name')
    def onchange_invoice_id(self):
        if self.name:
            self.amount_total = self.name.amount_receipt
            self.amount_residual = self.name.amount_residual

    @api.onchange('amount_receipt', 'amount_residual')
    # @api.depends('deposit_ids')
    def onchange_amount_receipt(self):
        if self.amount_receipt > self.amount_residual:
            raise UserError("ตัดยอดเกิน")

    name = fields.Many2one('ineco.customer.deposit', string=u'ใบมัดจำ', required=True, copy=False, index=True,
                           tracking=True)
    customer_id = fields.Many2one('res.partner', string=u'ลูกค้า',
                                  related='name.customer_id'
                                  , tracking=True)
    amount_total = fields.Float(string=u'ยอดตามบิล', copy=False, tracking=True)
    amount_residual = fields.Float(string=u'ยอดคงเหลือ', copy=False, tracking=True)
    pay_amount_receipt = fields.Float(string=u'ยอดชำระ', copy=False, tracking=True)
    amount_receipt = fields.Float(string=u'จำนวนชำระ', copy=False, tracking=True,
                                  related='move_line.price_unit')
    payment_id = fields.Many2one('ineco.customer.payment', string=u'รับชำระ')
    supplier_payment_id = fields.Many2one('ineco.supplier.payment', string=u'จ่ายชำระ')
    invoice_id = fields.Many2one('account.move', string=u'ใบแจ้งหนี้/ใบกำกับภาษี')
    move_line = fields.Many2one('account.move.line', string=u'Move line', ondelete="restrict")

    def update_deposit(self):
        quantity = -1
        company = self.env['res.company'].search([('id', '=', self.env.company.id)])
        if self.invoice_id.type == 'out_invoice':
            account_id = company.unearned_income_account_id.id
        else:
            account_id = company.unearned_expense_account_id.id

        tax = False
        if self.invoice_id.invoice_line_ids:
            if self.invoice_id.invoice_line_ids[0].tax_ids:
                # raise UserError('ยังไม่ได้ระบุการคิดภาษี')
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
            }
            aml = self.env['account.move.line'].search(
                [('customer_deposit_ids', '=', cut.name.id), ('move_id', '=', self.invoice_id.id)])
            if not aml:
                aml = self.env['account.move.line'].create(data)
            cut.update({'move_line': aml.id})


class InecoCustomerPaymentLine(models.Model):
    _name = 'ineco.customer.payment.line'
    _description = 'Customer Payment Line'

    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.onchange('name')
    def onchange_invoice_id(self):
        if self.name:
            self.gl_receivable = self.name.move_id.amount_residual_signed
            self.amount_total = self.name.move_id.amount_total_signed
            self.amount_residual = self.name.amount_residual
            if self.name.move_id.move_type == 'out_invoice':
                self.amount_receipt = self.name.amount_residual
            if self.name.move_id.move_type == 'out_refund':
                self.amount_receipt = - (self.name.amount_residual)
        # self.change_name()

    @api.depends('name', 'amount_receipt')
    def _compute_gl_receivable(self):
        difference = 0.0
        for iv in self:
            iv.clear_debtor = iv.amount_receipt * iv.payment_id.rate
            difference = (iv.payment_id.rate - iv.name.move_id.rate) * iv.amount_receipt
            iv.difference = difference

    name = fields.Many2one('account.move.line', string=u'ใบแจ้งหนี้/ใบกำกับภาษี', required=True, copy=False, index=True,
                           domain="[('amount_residual','>',0.0)]",
                           tracking=True)
    date_invoice = fields.Date(string=u'ลงวันที่', related='name.date', readonly=True)
    billing_id = fields.Many2one('ineco.billing', string=u'เลขที่ใบวางบิล', related='name.move_id.billing_id',
                                 copy=False,
                                 index=True, tracking=True, readonly=True)
    user_id = fields.Many2one('res.users', string=u'พนักงานขาย', index=True, tracking=True)
    amount_total = fields.Float(string=u'ยอดตามบิล', copy=False, tracking=True)
    amount_residual = fields.Float(string=u'ยอดค้างชำระ', copy=False, tracking=True)
    amount_receipt = fields.Float(string=u'ยอดชำระ', copy=False, tracking=True)
    payment_id = fields.Many2one('ineco.customer.payment', string=u'รับชำระ')
    gl_receivable = fields.Float(string=u'GLลูกหนี้', copy=False, tracking=True,
                                 # compute='_compute_gl_receivable' ,
                                 digits=(12, 2),
                                 store=True)
    clear_debtor = fields.Float(string=u'ล้างลูกหนี้', copy=False, tracking=True,
                                compute='_compute_gl_receivable', digits=(12, 2)

                                )
    difference = fields.Float(string=u'ส่วนต่าง', copy=False, tracking=True,
                              compute='_compute_gl_receivable', digits=(12, 2),
                              )
    rate = fields.Float(string=u'Rate IV')

    foreign = fields.Boolean(u'ต่างประเทศ')

    @api.onchange('name')
    def _onchange_currency_id(self):
        for line in self:
            line.payment_id.get_currency_rates()

    def UpDateDone(self):
        if self.billing_id:
            self.billing_id.UpDateDone()
    # #
    # @api.onchange()
    # def update_gl_receivable(self):
    #     qty = 0.0
    #     qty = self.amount_receipt * self.rate
    #     return qty


class InecoCustomerPaymentOther(models.Model):
    _name = 'ineco.customer.payment.other'
    _description = 'Customer Payment Other'
    _order = 'dr'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.depends('name', 'dr', 'cr')
    def _compute_amount(self):
        for line in self:
            dr = line.dr
            cr = line.cr
            line.amount = dr - cr

    name = fields.Many2one('account.account', string=u'ผังบัญชี', required=True, copy=False, index=True,
                           tracking=True)
    dr = fields.Float(string=u'Dr', copy=False, tracking=True)
    cr = fields.Float(string=u'Cr', copy=False, tracking=True)
    amount = fields.Float(string=u'จำนวนเงิน', copy=False, tracking=True,
                          compute="_compute_amount", store=True)
    payment_id = fields.Many2one('ineco.customer.payment', string=u'รับชำระ')

    # @api.onchange('dr', 'cr')
    # def _onchange_amount(self):
    #     self.amount = self.cr - self.dr
    #     # self.amount = -self.cr


class InecoCustomerPaymentTransfer(models.Model):
    _name = 'ineco.customer.payment.transfer'
    _description = 'Customer Payment Transfer'

    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.depends('name', 'dr', 'cr')
    def _compute_amount(self):
        for line in self:
            dr = line.dr
            cr = line.cr
            line.amount = dr - cr

    name = fields.Many2one('account.account', string=u'ผังบัญชี', required=True, copy=False, index=True,
                           tracking=True)
    dr = fields.Float(string=u'Dr', copy=False, tracking=True)
    cr = fields.Float(string=u'Cr', copy=False, tracking=True)

    amount = fields.Float(string=u'จำนวนเงิน', copy=False, tracking=True,
                          compute="_compute_amount", store=True)
    payment_id = fields.Many2one('ineco.customer.payment', string=u'รับชำระ')


class InecoCustomerPaymentExchangeRate(models.Model):
    _name = 'ineco.customer.payment.exchange.rate'
    _description = 'Customer Payment Transfer'
    _order = 'dr'

    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Many2one('account.account', string=u'ผังบัญชี', required=True, copy=False, index=True,
                           tracking=True)
    dr = fields.Float(string=u'Dr', copy=False, tracking=True)
    cr = fields.Float(string=u'Cr', copy=False, tracking=True)
    payment_id = fields.Many2one('ineco.customer.payment', string=u'รับชำระ')
