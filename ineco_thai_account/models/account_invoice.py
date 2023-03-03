# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
import time

from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    name = fields.Char(string='Number', copy=False, readonly=False, store=True,
                       default='/', index=True, tracking=True, )
    change_number = fields.Boolean(string=u'Change Number', )
    billing_id = fields.Many2one('ineco.billing', string=u'ใบวางบิล', copy=False, tracking=True, )
    customer_deposit_ids = fields.One2many('ineco.customer.payment.deposit', 'invoice_id', string=u'มัดจำ',
                                           tracking=True, )
    supplier_deposit_ids = fields.One2many('ineco.supplier.payment.deposit', 'invoice_id', string=u'จ่ายมัดจำ',
                                           tracking=True, )
    partner_code = fields.Char(string=u'รหัส', related='partner_id.ref', readonly=True, tracking=True, )
    ineco_reconciled_tax = fields.Many2one('ineco.account.vat', string='ineco_reconciled')
    select_pay = fields.Boolean('ทำจ่าย/รับชำระ')
    sale_order_id = fields.Many2one('sale.order', string='Sale Order', tracking=True, copy=True)

    expense = fields.Boolean(u'บันทึกค่าใช้จ่าย',
                             related='journal_id.expense',
                             tracking=True,
                             store=True, readonly=True,
                             related_sudo=False
                             )
    ex_sale = fields.Boolean(u'ขายตัวอย่าง',
                             related='journal_id.ex',
                             tracking=True,
                             store=True, readonly=True,
                             related_sudo=False
                             )

    type = fields.Selection([
        ('out_invoice', 'Customer Invoice'),
        ('in_invoice', 'Vendor Bill'),
        ('out_refund', 'Customer Credit Note'),
        ('in_refund', 'Vendor Credit Note'),
        ('expense', u'ค่าใช้จ่าย')
    ], readonly=True, index=True, change_default=True,
        default=lambda self: self._context.get('type', 'out_invoice'),
        tracking=True, string='Type of Invoice')

    ineco_vat_ids = fields.One2many('ineco.account.vat', 'invoice_id', string=u'ภาษีพัก',
                                    domain=[('tax_purchase_wait_ok', '=', True)]
                                    # domain="[('tax_purchase_wait_ok','=',True)]"
                                    )
    ineco_vat_purchase_ids = fields.One2many('ineco.account.vat', 'invoice_id', string=u'ภาษีซื้อ',
                                             domain=[('tax_purchase_ok', '=', True), ('move_line_id', '!=', False)]
                                             # domain="[('tax_purchase_wait_ok','=',True)]"
                                             )
    is_vat = fields.Boolean(u'ยื่นยันภาษี', tracking=True, )

    tax_purchase_wait_ok = fields.Boolean(string=u'Purchase Tax wait', copy=False,
                                          # compute="_compute_tax_purchase_wait_ok",
                                          tracking=True,
                                          store=False)

    ineco_vat_sale_ids = fields.One2many('ineco.account.vat', 'invoice_id', string=u'ภาษีขาย',
                                         domain=[('tax_sale_ok', '=', True), ('move_line_id', '!=', False)]
                                         # domain="[('tax_purchase_wait_ok','=',True)]"
                                         )
    partner_customer_domain = fields.Boolean(u'customer domain', default=False)
    partner_supplier_domain = fields.Boolean(u'supplier domain', default=False)

    rate = fields.Float(digits=(12, 6), default=1.0, help='The rate of the currency to the currency of rate 1')
    internal_number = fields.Char(string="Number", copy=False, tracking=True,
                                  help="Unique number of the invoice, computed automatically when the invoice is created.")
    from_ip = fields.Char(string="มาจากไอพี")
    from_id = fields.Char(string="มาจากไอดี", index=True)
    temp_state = fields.Char(string="Temp State")
    temp_number = fields.Char(string="Temp Number")

    # ตัดอ้างอิงใบกำกับ
    def InecoReconcile(self):
        # self.customer_id.property_account_receivable_id.id
        # [('move_type', '=', 'out_refund')]
        if self.move_type == 'out_refund':
            account_id = self.partner_id.property_account_receivable_id
            if account_id.id != self.reversed_entry_id.partner_id.property_account_receivable_id.id:
                raise UserError(_(f'ผังลูกหนี้ไม่ตรงกัน :ใบกำกับอ้างอิง {account_id.code}-{account_id.name}'))
        elif self.move_type == 'in_refund':
            account_id = self.partner_id.property_account_payable_id
            if account_id.id != self.reversed_entry_id.partner_id.property_account_payable_id.id:
                raise UserError(_(f'ผังเจ้าหนี้ไม่ตรงกัน :ใบกำกับอ้างอิง {account_id.code}-{account_id.name}'))

        invoice_ids = []
        invoice_ids.append(self.reversed_entry_id.id)
        invoice_ids.append(self.id)
        domain = [('account_id', '=', account_id.id),
                  ('move_id', 'in', invoice_ids),
                  ('partner_id', '=', self.partner_id.id),
                  ('amount_residual', '!=', 0.0),
                  ]
        move_lines = self.env['account.move.line'].search(domain)
        move_lines.reconcile()

    @api.onchange('currency_id')
    def _onchange_currency_id(self):
        rate_obj = self.env['res.currency.rate']
        if self.currency_id.id == self.company_id.currency_id.id:
            self.rate = 1.0
        else:
            rate = rate_obj.search([
                ('currency_id', '=', self.currency_id.id),
                ('name', '=', self.invoice_date),
            ])
            if not rate:
                res = {}
                res['warning'] = {
                    'title': ("มีเงินมัดจ่ายมัดจำ"),
                    'message': 'ค้นหาค่าเงินไม่เจอกรุณาระบุ'
                }
                self.update({'rate': 0.0})
                return res
            else:
                currency_rates = self.currency_id._get_rates(self.company_id, self.invoice_date)
                rate = currency_rates.get(self.currency_id.id)
                self.update({'rate': rate})

    @api.onchange('rate')
    def _onchange_currency_id2(self):
        rate_obj = self.env['res.currency.rate']
        if self.currency_id.id == self.company_id.currency_id.id:
            self.rate = 1.0
        else:
            rate = rate_obj.search([
                ('currency_id', '=', self.currency_id.id),
                ('name', '=', self.invoice_date),
                ('rate', '=', self.rate)
            ])
            if not rate:
                rate_obj.create({'currency_id': self.currency_id.id, 'rate': self.rate, 'name': self.invoice_date})
            else:
                raise UserError(_(u'rate ซ้ำในวันที่ดังกล่าว รบกวนแก้ไข rate ค่าเงินนั้นๆก่อน'))

    @api.onchange('partner_id', 'invoice_date')
    def _onchange_partner_deposit(self):
        if not self.invoice_date:
            self.get_update_deposit()
            warning = {}
            deposits = self.env['ineco.customer.deposit'].search(
                [('customer_id', '=', self.partner_id.id), ('state', '=', 'post'),
                 ('amount_residual', '>', 0.0)])
            note = []
            for de in deposits:
                message = f'เลขที่เอกสารมัดจำ {de.name} คงเหลือ {de.amount_residual} บาท '
                note.append(message)
            note2 = ''
            for n in note:
                note2 += n + '\n'
            if deposits:
                warning = {
                    'title': ("มีเงินมัดจ่ายมัดจำ"),
                    'message': note2
                }
            res = {}
            if warning:
                res['warning'] = warning
            return res

    def button_get_update_deposit(self):
        self.get_update_deposit()
        return True

    def get_update_deposit(self):
        if self.move_type not in ('entry', 'out_refund', 'in_refund'):
            deposits = self.env['ineco.customer.deposit'].search(
                [('customer_id', '=', self.partner_id.id), ('state', '=', 'post'),
                 ('amount_residual', '>', 0.0)])
            for deposit in deposits:
                cut_iv = self.env['ineco.customer.payment.deposit'].search([('name', '=', deposit.id),
                                                                            ('invoice_id', '=', self.id)])
                if not cut_iv:
                    cut = self.env['ineco.customer.payment.deposit'].create({
                        'name': deposit.id,
                        'amount_total': deposit.amount_deposit,
                        'amount_residual': deposit.amount_residual,
                        'invoice_id': self.id,
                    })

    def delete_deposit(self):
        for line in self.customer_deposit_ids:
            if line.amount_receipt == 0.0:
                line.unlink()

    def create_history_deposit(self):
        for line in self.invoice_line_ids:
            if line.customer_deposit_ids:
                if line.price_unit <= 0.0:
                    raise UserError("กรุณาระบุจำนวนตัดมัดจำด้วยครับ!")
                if line.price_unit > line.customer_deposit_ids.amount_residual:
                    raise UserError("ยอดตัดมัดจำมากกว่า ยอดคงค้าง เลขที่ {} จำนวนคงค้างที่ตัดได้ {}".format(
                        line.customer_deposit_ids.name, line.customer_deposit_ids.amount_residual))
                line.customer_deposit_ids.create_history(line.price_unit, self.name)

    def delete_history_deposit(self):
        for line in self.invoice_line_ids:
            if line.customer_deposit_ids:
                line.customer_deposit_ids.delete_history(self.name)

    def get_currency_rates(self):
        currency_rates = self.currency_id._get_rates(self.company_id, self.invoice_date)
        rate = currency_rates.get(self.currency_id.id)
        self.update({'rate': rate})

    def action_post(self):
        if self.internal_number and self.change_number:
            self.name = self.internal_number
        else:
            if self.name == '/':
                if not self.journal_id.secure_sequence_id:
                    raise UserError("กรุณาระบุลำดับเลขที่เอกสาร")
                if self.move_type not in ['out_invoice']:
                    self.name = self.journal_id.secure_sequence_id.next_by_id()
                else:
                    self.name = self.journal_id.secure_sequence_id.next_by_id(self.invoice_date)
        if self.move_type in ['out_invoice', 'out_refund']:
            self.get_currency_rates()
        res = super(AccountMove, self).action_post()
        self.create_history_deposit()
        self.delete_deposit()
        # สร้าง ineco.account.vat
        account_sale_tax_id = self._get_sale_vat_account_id()
        account_purchase_tax_id = self._get_purchase_vat_account_id()
        account_id = account_purchase_tax_id or account_sale_tax_id
        # print('account_id',account_id)
        if account_id:
            self.create_vat()
        # self.change_number = False
        return res

    def button_draft(self):
        res = super(AccountMove, self).button_draft()
        self.delete_history_deposit()
        self.get_update_deposit()
        self.delete_vat()
        return res

    def button_cancel(self):
        res = super(AccountMove, self).button_cancel()
        self.delete_history_deposit()
        return res

    @api.onchange('move_type')
    def _onchange_type(self):
        if self.move_type in ('in_invoice', 'in_refund', 'in_receipt'):
            self.partner_supplier_domain = True
            self.partner_customer_domain = False
        elif self.move_type in ('out_invoice', 'out_refund', 'out_receipt'):
            self.partner_supplier_domain = False
            self.partner_customer_domain = True

    def delete_vat(self):
        invoices = self.env['ineco.account.vat'].search([('invoice_id', '=', self.id)])
        if invoices:
            invoices.unlink()

    def _get_sale_vat_account_id(self):
        self.ensure_one()
        for line in self.line_ids:
            if line.account_id.tax_sale_ok:
                return line.account_id.id, line.id
        return False, False

    def _get_purchase_vat_account_id(self):
        self.ensure_one()
        for line in self.line_ids:
            if line.account_id.tax_purchase_ok:
                return line.account_id.id, line.id
        return False, False

    def create_vat(self):
        ineco_account_vat_obj = self.env['ineco.account.vat']
        account_sale_tax_id, move_sale_line_id = self._get_sale_vat_account_id()
        account_purchase_tax_id, move_purchase_line_id = self._get_purchase_vat_account_id()
        account_id = account_purchase_tax_id or account_sale_tax_id
        move_line_id = move_sale_line_id or move_purchase_line_id
        if self.move_type in ('out_invoice'):
            vat_data = {
                'invoice_id': self.id,
                'name': self.name,
                'docdat': self.invoice_date,
                'partner_id': self.partner_id.id,
                'taxid': self.partner_id.vat or '',
                'depcod': self.partner_id.branch_no or '00000',
                'amount_untaxed': self.amount_untaxed,
                'amount_tax': self.amount_tax,
                'amount_total': self.amount_total,
                'tax_sale_ok': True,
                'tax_purchase_ok': False,
                'partner_name': self.partner_id.name,
                'period_id': self.period_id.id,
                'account_id': account_id,
                'move_line_id': move_line_id
            }
            ineco_account_vat_obj.create(vat_data)
        elif self.move_type in ('out_refund'):
            vat_data = {
                'invoice_id': self.id,
                'name': self.name,
                'docdat': self.invoice_date,
                'partner_id': self.partner_id.id,
                'taxid': self.partner_id.vat or '',
                'depcod': self.partner_id.branch_no or '00000',
                'amount_untaxed': -self.amount_untaxed,
                'amount_tax': -self.amount_tax,
                'amount_total': -self.amount_total,
                'tax_sale_ok': True,
                'tax_purchase_ok': False,
                'partner_name': self.partner_id.name,
                'period_id': self.period_id.id,
                'account_id': account_id,
                'move_line_id': move_line_id
            }
            ineco_account_vat_obj.create(vat_data)
        elif self.move_type in ('in_invoice'):
            vat_data = {
                'invoice_id': self.id,
                'name': self.name,
                'docdat': self.invoice_date,
                'partner_id': self.partner_id.id,
                'taxid': self.partner_id.vat or '',
                'depcod': self.partner_id.branch_no or '00000',
                'amount_untaxed': self.amount_untaxed,
                'amount_tax': self.amount_tax,
                'amount_total': self.amount_total,
                'tax_sale_ok': False,
                'tax_purchase_ok': True,
                'partner_name': self.partner_id.name,
                'period_id': self.period_id.id,
                'account_id': account_id,
                'move_line_id': move_line_id
            }
            ineco_account_vat_obj.create(vat_data)
        elif self.move_type in ('in_refund'):
            vat_data = {
                'invoice_id': self.id,
                'name': self.name,
                'docdat': self.invoice_date,
                'partner_id': self.partner_id.id,
                'taxid': self.partner_id.vat or '',
                'depcod': self.partner_id.branch_no or '00000',
                'amount_untaxed': -self.amount_untaxed,
                'amount_tax': -self.amount_tax,
                'amount_total': -self.amount_total,
                'tax_sale_ok': False,
                'tax_purchase_ok': True,
                'partner_name': self.partner_id.name,
                'period_id': self.period_id.id,
                'account_id': account_id,
                'move_line_id': move_line_id
            }
            ineco_account_vat_obj.create(vat_data)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"
    _description = "Journal Item"
    _order = "debit desc, credit desc"

    customer_deposit_ids = fields.Many2one('ineco.customer.deposit', string=u'มัดจำ')
    pay_id_thai = fields.Many2one('account.move.line', string=u'ใบแจ้งหนี้/ใบกำกับภาษี', copy=False)
    invoice_id = fields.Many2one('account.move', string=u'ใบแจ้งหนี้/ใบกำกับภาษี', copy=False)
    # supplier_deposit_ids = fields.Many2one('ineco.supplier.payment.deposit', 'invoice_id', string=u'จ่ายมัดจำ')
