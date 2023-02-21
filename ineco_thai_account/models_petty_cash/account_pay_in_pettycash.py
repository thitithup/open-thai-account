# -*- coding: utf-8 -*-

from calendar import monthrange
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.tools import float_compare, float_is_zero


class InecoPayInPettyCash(models.Model):
    _name = 'ineco.pay.in.petty.cash'
    _description = 'Petty Cash'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    @api.depends('cheque_ids')
    def _get_cheque(self):
        for receipt in self:
            receipt.amount_cheque = 0.0
            for cheque in receipt.cheque_ids:
                receipt.amount_cheque += cheque.amount

    name = fields.Char(u'เลขที่ทำจ่าย', readonly=True)
    date = fields.Date(u'วันที่', readonly=True)
    journal_id = fields.Many2one('account.journal', string=u'สมุดบัญชี')
    move_id = fields.Many2one('account.move', string=u'GL', index=True, readonly=True)

    control_id = fields.Many2one('ineco.petty.cash', string='Petty Cash Control')

    debit_account_id = fields.Many2one('account.account', related='control_id.account_id', string=u'เข้าผังบัญชี')

    credit_account_id = fields.Many2one('account.account', string=u'จากผังบัญชี')

    department_id = fields.Many2one('hr.department', string='Department')
    state = fields.Selection(string="state",
                             selection=[('pending', u'รอดำเนินการ'), ('done', u'Post')],
                             default='pending')
    amount_residual = fields.Float('คงเหลือ', digits=(16, 2), tracking=True)
    amount_withdraw = fields.Float('วงเงินที่ต้องการเบิก', digits=(16, 2), tracking=True)

    date_start = fields.Date(string=u'จากวันที่', required=False)
    date_end = fields.Date(string=u'ถึงวันที่', required=False)

    amount_control_residual = fields.Float('วงเงินคงเหลือ', digits=(16, 2), tracking=True,
                                           related='control_id.amount_residual')

    line_ids = fields.One2many('ineco.pay.in.petty.cash.line', 'control_id', string=u'รายละเอียด')

    cheque_ids = fields.One2many('ineco.cheque', 'pay_expense_id', string=u'รายการเช็ค')
    amount_cash = fields.Float(string=u'เงินสด', tracking=True, copy=False)
    amount_cheque = fields.Float(string=u'เช็คจ่าย', tracking=True,
                                 compute='_get_cheque',
                                 copy=False)
    company_id = fields.Many2one('res.company', string='Company', store=True, readonly=True, change_default=True,
                                 default=lambda self: self.env.company)

    def petty_1(self):
        name = self.name
        self.control_id.create_history(self.amount_withdraw, 0.0, name, self.move_id.id)

    def button_post(self):
        self.ensure_one()
        if round(self.amount_withdraw, 2) != round(self.amount_cash, 2) + round(self.amount_cheque, 2):
            raise UserError("ยอดจ่าย กับ ยอดไม่ สมดุล")
        move = self.env['account.move']
        iml = []
        move_line = self.env['account.move.line']
        params = self.env['ir.config_parameter'].sudo()

        receivable_account_id = self.debit_account_id.id
        move_data_vals = {
            'partner_id': False,
            # 'invoice_id': False,
            'debit': round(self.amount_cheque + self.amount_cash, 2),
            'credit': 0.0,
            'payment_id': False,
            'account_id': receivable_account_id,
        }
        iml.append((0, 0, move_data_vals))

        # Debit Side

        cash_account_id = self.env.company.cash_account_id.id
        if self.amount_cash:
            move_data_vals = {
                'partner_id': False,
                # 'invoice_id': False,
                'credit': self.amount_cash,
                'debit': 0.0,
                'payment_id': False,
                'account_id': cash_account_id,
            }
            iml.append((0, 0, move_data_vals))
        cheque_sale_account_id = self.env.company.cheque_purchase_account_id.id
        if self.amount_cheque:
            move_data_vals = {
                'partner_id': False,
                # 'invoice_id': False,
                'credit': self.amount_cheque,
                'debit': 0.0,
                'payment_id': False,
                'account_id': cheque_sale_account_id,
            }
            iml.append((0, 0, move_data_vals))

        move_vals = {
            # 'ref': self.name,
            'date': datetime.now(),
            'date_due': datetime.now(),
            'company_id': self.env.company.id,
            'journal_id': self.journal_id.id,
            # 'partner_id': self.address_id.id,
        }
        new_move = move.create(move_vals)
        new_move.sudo().write({'line_ids': iml})
        new_move.post()
        self.move_id = new_move
        if not self.date:
            self.date = self.move_id.date
        self.write({'state': 'done'})
        self.petty_1()
        return True

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('ineco.pay.in.petty.cash')
        petty = super(InecoPayInPettyCash, self.with_context(mail_create_nosubscribe=True)).create(vals)
        return petty


class KKPayPettyCashControlLine(models.Model):
    _name = 'ineco.pay.in.petty.cash.line'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    date = fields.Date(u'วันที่', tracking=True)
    control_id = fields.Many2one('ineco.pay.in.petty.cash', string='Petty Cash Control')
    name = fields.Char('Descriptions', tracking=True)
    employee_id = fields.Many2one('hr.employee', string="Employee")
    department_id = fields.Many2one('hr.department', string='แผนก', )
    total_amount = fields.Float(string='Total Amount')
