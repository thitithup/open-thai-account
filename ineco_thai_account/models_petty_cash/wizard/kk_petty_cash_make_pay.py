# -*- coding: utf-8 -*-

from odoo import _, api, exceptions, fields, models
from odoo.exceptions import UserError


class InecoPettyCashMakePay(models.TransientModel):
    _name = "ineco.petty.cash.make.pay"
    _inherit = ['mail.thread']

    @api.model
    def _control_id_get(self):
        active_id = self._context.get('active_id', False)
        petty_obj = self.env['ineco.petty.cash']
        line = petty_obj.search([('id', '=', active_id)])
        # print('line', line)
        return line.id

    @api.depends('item_ids')
    def _get_amount(self):
        amount = 0.0
        for iv in self.item_ids:
            amount += iv.total_amount
        self.amount = amount

    date_start = fields.Date(string=u'จากวันที่', required=False)
    date_end = fields.Date(string=u'ถึงวันที่', required=False)
    control_id = fields.Many2one('ineco.petty.cash', string='Petty Cash Control', default=_control_id_get, )

    amount = fields.Float('วงเงินที่ต้องเบิก', digits=(16, 2), tracking=True, compute='_get_amount')
    amount_control = fields.Float('วงเงินรวม', digits=(16, 2), tracking=True,
                                  related='control_id.amount_control')
    item_ids = fields.One2many('ineco.petty.cash.make.pay.line', 'wiz_id', string='Items')

    amount_withdraw = fields.Float('วงเงินที่ต้องการเบิกเพิ่มเติม', digits=(16, 2), tracking=True)

    @api.onchange('amount', 'amount_withdraw')
    def _onchange_amount(self):
        if self.amount > self.amount_control:
            raise UserError(_("รายการขอเบิกมากว่าวงเงิน"))
            self.amount = 0.0
            self.update({'amount': 0.0})

    def action_update(self):
        expense_obj = self.env['account.move'].search([
            # ('cash_id', '=', self.control_id.id),
            # ('date_invoice', '>=', self.date_start),
            # ('date_invoice', '<=', self.date_end),
            # ('state', 'in', ['open', 'paid']),
        ], limit=1)

        line_obj = self.env['ineco.petty.cash.make.pay.line']
        for expense in expense_obj:
            data = {
                'wiz_id': self.id,
                'date': False,
                'name': False,
                'employee_id': False,
                'department_id': False,
                'total_amount': False,
                'expense_id': expense.id
            }
            searchs = line_obj.search([('sheet_id', '=', expense.id),
                                       ('wiz_id', '=', self.id)])
            if not searchs:
                line_obj.create(data)
        return {'type': 'ir.actions.act_close_wizard_and_reload_view'}

    def create_pay(self):
        pay_obj = self.env['ineco.pay.in.petty.cash']
        pay_line_obj = self.env['ineco.pay.in.petty.cash.line']
        qty = 0.0
        if self.amount > 0.0:
            qty = self.amount
        journal_id = self.env['account.journal'].search([('petty', '=', True)], limit=1)
        if not journal_id:
            raise UserError("กรุณาติดต่อผู้ดแล เพื่อสมุดรายวันเพื่อเติมเงินสดในมือ")
        data = {
            'amount_residual': self.control_id.amount_residual,
            # 'date_start':self.date_start,
            # 'date_end':self.date_end,
            'control_id': self.control_id.id,
            'amount_withdraw': qty + self.amount_withdraw,
            'department_id': self.control_id.department_id.id,
            'journal_id': journal_id.id

        }
        # print(data)
        pay_id = pay_obj.create(data)
        # pay_id.update_pay()
        # for line in self.item_ids:
        #     data_line = {
        #         'date': line.date,
        #         'name': line.name,
        #         'employee_id': line.employee_id.id,
        #         'department_id': line.department_id.id,
        #         'total_amount': line.total_amount,
        #         'control_id': pay_id.id
        #     }
        #     pay_line_obj.create(data_line)

        view_ref = self.env['ir.model.data'].check_object_reference('ineco_thai_account', 'ineco_pay_petty_cash_form')
        view_id = view_ref and view_ref[1] or False,
        return {
            'type': 'ir.actions.act_window',
            'name': 'ineco.pay.in.petty.cash.form',
            'res_model': 'ineco.pay.in.petty.cash',
            'res_id': pay_id.id,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'current',
            'nodestroy': True,
        }


class InecoPettyCashMakePayLine(models.TransientModel):
    _name = "ineco.petty.cash.make.pay.line"

    wiz_id = fields.Many2one('ineco.petty.cash.make.pay', string='Wizard', required=True, ondelete='cascade',
                             readonly=True)
    # sheet_id = fields.Many2one('hr.expense.sheet', string=u'รายละเอียด')
    # expense_id = fields.Many2one('account.invoice', string=u'รายละเอียด')
    date = fields.Date(u'วันที่')
    name = fields.Char(u'ชื่อ')
    employee_id = fields.Many2one('hr.employee', string="Employee")
    department_id = fields.Many2one('hr.department', string='แผนก', )
    total_amount = fields.Float(string='Total Amount')
