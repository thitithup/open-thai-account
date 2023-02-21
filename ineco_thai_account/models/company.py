# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class ResCompany(models.Model):
    _inherit = "res.company"

    cash_account_id = fields.Many2one('account.account', string=u'เงินสด', required=False)
    # Account Receivable
    interest_income_account_id = fields.Many2one('account.account', string=u'ดอกเบี้ยรับ', required=False)
    cash_discount_account_id = fields.Many2one('account.account', string=u'ส่วนลดเงินสด', required=False)
    wht_sale_account_id = fields.Many2one('account.account', string=u'ภาษีถูกหัก ณ ที่จ่าย', required=False)
    cheque_sale_account_id = fields.Many2one('account.account', string=u'เช็ครับ', required=False)
    vat_sale_account_id = fields.Many2one('account.account', string=u'ภาษีขาย', required=False)
    vat_sale_tax_break_account_id = fields.Many2one('account.account', string=u'ภาษีขายพัก', required=False)
    unearned_income_account_id = fields.Many2one('account.account', string=u'รายได้รับล่วงหน้า', required=False)
    # Account Payable
    interest_expense_account_id = fields.Many2one('account.account', string=u'ดอกเบี้ยจ่าย', required=False)
    cash_income_account_id = fields.Many2one('account.account', string=u'ส่วนลดรับ', required=False)
    wht_purchase_account_id = fields.Many2one('account.account', string=u'ภาษีหัก ณ ที่จ่าย', required=False)
    wht_purchase_personal_account_id = fields.Many2one('account.account', string=u'ภาษีหัก ณ ที่จ่าย (บุคคล)',
                                                       required=False)
    cheque_purchase_account_id = fields.Many2one('account.account', string=u'เช็คจ่าย', required=False)
    vat_purchase_account_id = fields.Many2one('account.account', string=u'ภาษีซื้อ', required=False)
    unearned_expense_account_id = fields.Many2one('account.account', string=u'รายจ่ายล่วงหน้า', required=False)
    vat_purchase_tax_break_account_id = fields.Many2one('account.account', string=u'ภาษีซื้อพัก', required=False)

    get_paid_account_id = fields.Many2one('account.account', string=u'-รับเงินขาด', required=False)
    get_overgrown_account_id = fields.Many2one('account.account', string=u'+รับเงินเกิน', required=False)
    profit_loss_account_id = fields.Many2one('account.account', string=u'+,- กำไรขาดทุนอัตราแลกเปลี่ยน', required=False)
    fee_account_id = fields.Many2one('account.account', string=u'ค่าธรรมเนียม', required=False)

    action_report_deposit_id = fields.Many2one('ir.actions.report', u'รูปแบบใบรับมัดจำ',
                                       copy=False)

    has_accounting_entries = fields.Boolean(
        string=u'INECO',
        readonly=False)

