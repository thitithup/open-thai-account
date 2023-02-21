# -*- coding: utf-8 -*-

from calendar import monthrange
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.tools import float_compare, float_is_zero


class InecoPettyCash(models.Model):
    _name = 'ineco.petty.cash'
    _description = 'Petty Cash'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    name = fields.Char(u'ชื่อเงินสดในมือ')
    account_id = fields.Many2one('account.account', string=u'ผนังบัญชี')
    amount_residual = fields.Float('วงเงินคงเหลือ', digits=(16, 2), tracking=True
                                   # ,compute='_get_receipts',store=True
                                   )
    amount_control = fields.Float('วงเงินรวม', digits=(16, 2), tracking=True)
    amount_min = fields.Float('วงเงินขั้นต่ำ', digits=(16, 2), tracking=True)
    department_id = fields.Many2one('hr.department', string='Department')
    state = fields.Selection(string="state",
                             selection=[('pending', u'รอดำเนินการ'), ('ok', u'ใช้งาน')],
                             default='pending')

    line_ids = fields.One2many('ineco.petty.cash.line', 'control_id',
                               string='ประวัติ')
    # pay_kk_id = fields.Many2one('kk.pay.petty.cash', string=u'ตั้งเบิกเงินสดย่อย', tracking=True,
    #                             copy=False)
    pay_in_ids = fields.One2many('ineco.pay.in.petty.cash', 'control_id', string=u'รายการใบกำกับ')
    pay_kk_count = fields.Integer(
        compute='_compute_pay_in',
        string=u'จำนวน', default=0, store=True)

    user_id = fields.Many2one('res.users', string='ผู้ดูแล', tracking=True,
                              # readonly=True,
                              # states={'pending': [('readonly', False)]},
                              copy=False)
    company_id = fields.Many2one('res.company', string='Company', store=True, readonly=True, change_default=True,
                                 default=lambda self: self.env.company)

    def name_get(self):
        res = []
        for record in self:
            name = ('%s คงเหลือ ( %s )' % (record.name, record.amount_residual))
            res.append((record.id, name))
        return res

    def approve(self):
        self.state = 'ok'

    def edit(self):
        self.state = 'pending'

    @api.depends('pay_in_ids')
    def _compute_pay_in(self):
        for requisition in self:
            requisition.pay_kk_count = len(requisition.pay_in_ids)


    def action_view_pay_in_petty(self):
        '''
        This function returns an action that display existing picking orders of given purchase order ids.
        When only one found, show the picking immediately.
        '''
        action = self.env.ref('ineco_thai_account.action_action_ineco_pay_petty_cash')
        result = action.read()[0]

        # override the context to get rid of the default filtering on operation type
        result['context'] = {}
        iv_ids = self.mapped('pay_in_ids')
        # choose the view_mode accordingly
        if not iv_ids or len(iv_ids) > 1:
            result['domain'] = "[('id','in',%s)]" % (iv_ids.ids)
        elif len(iv_ids) == 1:
            res = self.env.ref('ineco_thai_account.ineco_pay_petty_cash_form', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = iv_ids.id
        return result

    def create_history(self, receive_amount, pay_amount, name,move_id):
        balance_amount = 0.0
        if receive_amount:
            balance_amount = self.amount_residual + receive_amount
        if pay_amount:
            balance_amount = self.amount_residual - pay_amount

        self.env['ineco.petty.cash.line'].create({
            'date_amount': datetime.now(),
            'name': name,
            'control_id': self.id,
            'receive_amount': receive_amount,
            'pay_amount': pay_amount,
            'balance_amount': balance_amount,
            'move_id': move_id

        })
        self.amount_residual = balance_amount

    def delect_history(self,name):
        historys = self.env['ineco.petty.cash.line'].search([('name', '=', name)])
        for history in historys:
            history.unlink()


class InecoPettyCashControlLine(models.Model):
    _name = 'ineco.petty.cash.line'
    _description = 'Petty Cash Control History'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    name = fields.Char('Descriptions', tracking=True)
    control_id = fields.Many2one('ineco.petty.cash', string='Petty Cash Control')
    begin_amount = fields.Float('Beginning Balance', digits=(16, 2), tracking=True)
    receive_amount = fields.Float('Receive Amount', digits=(16, 2), tracking=True)
    pay_amount = fields.Float('Pay Amount', digits=(16, 2), tracking=True)
    balance_amount = fields.Float('Balance Amount', digits=(16, 2), tracking=True)
    date_amount = fields.Datetime('Date Amount', tracking=True)
    move_id = fields.Many2one('account.move', string=u'GL', index=True,readonly=True)
