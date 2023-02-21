# -*- coding: utf-8 -*-

from calendar import monthrange
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.tools import float_compare, float_is_zero


class InecoPettyCashInvioce(models.Model):
    _name = 'ineco.petty.cash.invoice'
    _description = 'Petty Cash'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    @api.depends('line_ids.total_amount', 'line_ids.quantity', 'line_ids.unit_amount',
                 'date', 'tax_type', 'amount_type_tax')
    def _compute_amount(self):
        amount = 0.0
        for line in self.line_ids:
            amount += line.total_amount
        if self.tax_type == 'percent':
            vat = amount * (self.amount_type_tax / 100)
            self.amount_tax = vat
            self.amount_untaxed = amount
            self.amount_total = amount + vat
        else:
            self.amount_untaxed = (amount * 100) / (100 + self.amount_type_tax)
            self.amount_tax = amount - (amount * 100) / (100 + self.amount_type_tax)
            self.amount_total = self.amount_untaxed + self.amount_tax

    name = fields.Char(u'เลขที่เอกสาร', default='New')
    ref = fields.Char(u'เลขที่อ้างอิง')
    date = fields.Date(string=u'ลงวันที่', required=True, default=fields.Date.context_today,
                       tracking=True)
    partner_id = fields.Many2one('res.partner', string=u'ผู้จำหน่าย', required=True, tracking=True)
    journal_id = fields.Many2one('account.journal', string=u'สมุดรายวัน', required=True, tracking=True)
    move_id = fields.Many2one('account.move', string=u'GL', index=True)
    cash_id = fields.Many2one('ineco.petty.cash', string='เงินในเมือ',
                              required=True, tracking=True)
    account_id = fields.Many2one('account.account', store=True,
                                 related='cash_id.account_id',
                                 string=u'เข้าผนังบัญชี')

    debit_account_id = fields.Many2one('account.account', string=u'ผังบัญชีค่าใช้จ่าย')

    analytic_tag_ids = fields.Many2many('account.analytic.tag',
                                        string='Analytic Tags',
                                        store=True, readonly=False)
    analytic_account_id = fields.Many2one('account.analytic.account',
                                          string='Analytic Account',
                                          store=True, readonly=False)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('post', 'Posted'),
        ('done', 'Paid'),
        ('cancel', 'Cancel')
    ], string='Status', index=True, readonly=True, tracking=True, copy=False, default='draft', required=True)

    line_ids = fields.One2many('ineco.petty.cash.invoice.line', 'invoice_id',
                               string='ประวัติ')

    tax_type = fields.Selection(default='percent', string="ประเภทภาษี", required=True,
                                selection=[('percent', 'ภาษีแยก'),
                                           ('included', u'ภาษีรวม')])
    tax_purchase_wait_ok = fields.Boolean(string=u'ภาษีซื้อ รอนำส่ง', copy=False, tracking=True,
                                          store=True)
    amount_type_tax = fields.Integer(required=True, default=7, string='อัตราภาษี')

    amount_untaxed = fields.Float(string='Untaxed Amount',
                                  digits='Product Price',
                                  store=True, readonly=True,
                                  compute='_compute_amount',
                                  tracking=True)
    amount_tax = fields.Float(string='Tax',
                              store=True, readonly=True, digits='Product Price',
                              compute='_compute_amount'
                              )
    amount_total = fields.Float(string='Total',
                                store=True, readonly=True,
                                compute='_compute_amount'
                                )

    wht_ids = fields.One2many('ineco.wht', 'cash_invoic_id', string=u'หัก ณ ที่จ่าย')
    company_id = fields.Many2one('res.company', string='Company', store=True, readonly=True, change_default=True,
                                 default=lambda self: self.env.company)

    def petty_1(self, amount_withdraw):
        name = self.name
        self.cash_id.create_history(0.0, amount_withdraw, name, self.move_id.id)

    def button_draft(self):
        self.ensure_one()
        self.move_id.button_cancel()
        if self.move_id.state == 'cancel':
            self.move_id = False
            self.state = 'draft'
        for line in self.move_id.line_ids:
            for vat in line.vat_ids:
                vat.unlink()
        return True

    def button_cancel(self):
        self.ensure_one()
        if self.move_id:
            self.move_id.button_draft()
            self.move_id.button_cancel()
        self.cash_id.delect_history(self.name)
        self.state = 'cancel'
        for line in self.move_id.line_ids:
            for vat in line.vat_ids:
                vat.unlink()
        return True

    def action_expense_post(self):
        self.ensure_one()
        if not self.date:
            raise ValidationError(u'โปรดระบุวันที่เอกสาร')
        move = self.env['account.move']
        iml = []

        property_account_expense_id = self.debit_account_id.id
        if self.amount_untaxed:
            move_data_vals = {
                'partner_id': False,
                'debit': round(self.amount_untaxed, 2),
                'credit': 0.0,
                'payment_id': False,
                'analytic_account_id': self.analytic_account_id.id,
                'analytic_tag_ids': [(6, 0, [x.id for x in self.analytic_tag_ids])],
                'account_id': property_account_expense_id,
            }
            iml.append((0, 0, move_data_vals))
        vat_purchase_account_id = self.env.company.vat_purchase_account_id.id
        date_vat = self.date
        if self.tax_purchase_wait_ok:
            vat_purchase_account_id = self.env.company.vat_purchase_tax_break_account_id.id
            date_vat = False
        if self.amount_tax > 0.0:
            move_data_vals = {
                'partner_id': False,
                'debit': round(self.amount_tax, 2),
                'credit': 0.0,
                'payment_id': False,
                'account_id': vat_purchase_account_id,
            }
            iml.append((0, 0, move_data_vals))

        wht_qty = 0.0
        for wht in self.wht_ids:
            wht_qty += wht.tax

        wht_purchase_account_id = self.env.company.wht_purchase_account_id.id

        if wht_qty > 0.0:
            move_data_vals = {
                'partner_id': False,
                'debit': 0.0,
                'credit': round(wht_qty, 2),
                'payment_id': False,
                'account_id': wht_purchase_account_id,
            }
            iml.append((0, 0, move_data_vals))

        move_data_vals = {
            'partner_id': False,
            'debit': 0.0,
            'credit': round(self.amount_untaxed, 2) + round(self.amount_tax - wht_qty, 2),
            'payment_id': False,
            'account_id': self.account_id.id,
        }

        iml.append((0, 0, move_data_vals))
        move_vals = {
            'date': datetime.now(),
            'date_due': datetime.now(),
            'company_id': self.env.company.id,
            'journal_id': self.journal_id.id,
        }
        new_move = move.create(move_vals)
        new_move.sudo().write({'line_ids': iml})
        new_move.post()

        self.move_id = new_move
        self.name = self.move_id.name
        if not self.date:
            self.date = self.move_id.date
        self.write({'state': 'done'})
        self.petty_1(round(self.amount_untaxed, 2) + round(self.amount_tax - wht_qty, 2))

        move_line = self.env['account.move.line'].search([
            ('move_id', '=', self.move_id.id),
            ('account_id', '=', vat_purchase_account_id)])
        period_id = self.env['ineco.account.period'].finds(dt=self.date)

        self.env['ineco.account.vat'].create({'tax_purchase_wait_ok': False,
                                              'move_line_id': move_line.id,
                                              'docdat': self.date,
                                              'vatprd': date_vat,
                                              'name': self.ref,
                                              'partner_id': self.partner_id.id,
                                              'partner_name': self.partner_id.name,
                                              'taxid': self.partner_id.vat or '',
                                              'depcod': self.partner_id.branch_no or 00000,
                                              'amount_untaxed': self.amount_untaxed,
                                              'amount_tax': self.amount_tax,
                                              'amount_total': self.amount_total,
                                              'account_id': vat_purchase_account_id,
                                              'period_id': period_id.id,
                                              })
        wht_move_line = self.env['account.move.line'].search([
            ('move_id', '=', self.move_id.id),
            ('account_id', '=', wht_purchase_account_id)])
        for wht in self.wht_ids:
            wht.write({'move_line_id':wht_move_line.id})
        return True


class InecoPettyCashInvoicelLine(models.Model):
    _name = 'ineco.petty.cash.invoice.line'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    @api.depends('unit_amount', 'quantity', 'name', 'product_id')
    def _compute_price(self):
        for line in self:
            line.total_amount = line.quantity * line.unit_amount

    name = fields.Char('Descriptions', tracking=True)
    invoice_id = fields.Many2one('ineco.petty.cash.invoice', string='Petty Cash Control')

    date = fields.Date(default=fields.Date.context_today, string="Expense Date")

    product_id = fields.Many2one('product.product', string='Product', tracking=True,
                                 # domain="[('can_be_expensed', '=', True)]",
                                 ondelete='restrict')
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    unit_amount = fields.Float("Unit Price", digits='Product Price')
    quantity = fields.Float(required=True, digits='Product Unit of Measure', default=1)
    untaxed_amount = fields.Float("Subtotal", store=True, digits='Account', )
    total_amount = fields.Float("Total", tracking=True, compute='_compute_price', digits='Product Price')
