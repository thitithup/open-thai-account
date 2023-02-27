# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class SequenceMixin(models.AbstractModel):
    _inherit = 'sequence.mixin'

    def _constrains_date_sequence(self):
        pass


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    type = fields.Selection(selection_add=[('receive', 'Receivable'), ('pay', 'Payable')],
                            ondelete={'receive': 'cascade', 'pay': 'cascade'})
    type_vat = fields.Selection([('a', u'VAT'), ('b', u'NO'), ], string=u'ประะเภทกิจกรรม')
    input_tax = fields.Boolean(u'กลับภาษี')
    name2 = fields.Char(u'ชื่อสำรอง')
    name_print = fields.Char(u'ชื่อใบสำคัญ')
    gl_description = fields.Char(u'คำอธิบายรายการ 1', )
    description = fields.Text(u'คำอธิบายรายการ 2', )
    foreign = fields.Boolean(u'ต่างประเทศ')
    ex = fields.Boolean(u'ขายตัวอย่าง')
    expense = fields.Boolean(u'บันทึกค่าใช้จ่าย')
    # New in V14
    default_debit_account_id = fields.Many2one('account.account', string='Default Debit Account')
    default_credit_account_id = fields.Many2one('account.account', string='Default Credit Account')
    bank_id = fields.Many2one('res.bank', string='Bank')

    petty = fields.Boolean(u'เงินสดในมือ')
    is_refund = fields.Boolean(u'ลดหนี้')
    is_add_dn = fields.Boolean(u'เพิ่มหนี้')
    is_deposit = fields.Boolean(u'มัดจำ')
    secure_sequence_id = fields.Many2one('ir.sequence',
                                         help='Sequence to use to ensure the securisation of data',
                                         check_company=True,
                                         readonly=False, copy=False)
