# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    has_accounting_entries = fields.Boolean(
        string=u'has_accounting_entries',
        related='company_id.has_accounting_entries',
        readonly=False)

    cash_account_id = fields.Many2one('account.account', string=u'เงินสด',
                                      required=False,
                                      related='company_id.cash_account_id',
                                      readonly=False
                                      )
    # Account Receivable
    interest_income_account_id = fields.Many2one('account.account', string=u'ดอกเบี้ยรับ', required=False,
                                                 related='company_id.interest_income_account_id', readonly=False)
    cash_discount_account_id = fields.Many2one('account.account', string=u'ส่วนลดเงินสด', required=False,
                                               related='company_id.interest_income_account_id', readonly=False
                                               )
    wht_sale_account_id = fields.Many2one('account.account', string=u'ภาษีถูกหัก ณ ที่จ่าย', required=False,
                                          readonly=False,
                                          related='company_id.wht_sale_account_id'
                                          )
    cheque_sale_account_id = fields.Many2one('account.account', string=u'เช็ครับ', required=False, readonly=False,
                                             related='company_id.cheque_sale_account_id')
    vat_sale_account_id = fields.Many2one('account.account', string=u'ภาษีขาย', required=False,
                                          related='company_id.vat_sale_account_id', readonly=False
                                          )
    vat_sale_tax_break_account_id = fields.Many2one('account.account', string=u'ภาษีขายพัก', required=False,
                                                    readonly=False,
                                                    related='company_id.vat_sale_tax_break_account_id'
                                                    )
    unearned_income_account_id = fields.Many2one('account.account', string=u'รายได้รับล่วงหน้า', required=False,
                                                 readonly=False,
                                                 related='company_id.unearned_income_account_id')
    # Account Payable
    interest_expense_account_id = fields.Many2one('account.account', string=u'ดอกเบี้ยจ่าย', required=False,
                                                  readonly=False,
                                                  related='company_id.interest_expense_account_id'
                                                  )
    cash_income_account_id = fields.Many2one('account.account', string=u'ส่วนลดรับ', required=False, readonly=False,
                                             related='company_id.cash_income_account_id')
    wht_purchase_account_id = fields.Many2one('account.account', string=u'ภาษีหัก ณ ที่จ่าย', required=False,
                                              readonly=False,
                                              related='company_id.wht_purchase_account_id'
                                              )
    wht_purchase_personal_account_id = fields.Many2one('account.account', string=u'ภาษีหัก ณ ที่จ่าย (บุคคล)',
                                                       related='company_id.wht_purchase_personal_account_id',
                                                       readonly=False,
                                                       required=False)
    cheque_purchase_account_id = fields.Many2one('account.account', string=u'เช็คจ่าย', required=False, readonly=False,
                                                 related='company_id.cheque_purchase_account_id'
                                                 )
    vat_purchase_account_id = fields.Many2one('account.account', string=u'ภาษีซื้อ', required=False, readonly=False,
                                              related='company_id.vat_purchase_account_id'
                                              )
    unearned_expense_account_id = fields.Many2one('account.account', string=u'รายจ่ายล่วงหน้า', required=False,
                                                  readonly=False,
                                                  related='company_id.unearned_expense_account_id'
                                                  )
    vat_purchase_tax_break_account_id = fields.Many2one('account.account', string=u'ภาษีซื้อพัก', required=False,
                                                        readonly=False,
                                                        related='company_id.vat_purchase_tax_break_account_id'
                                                        )

    get_paid_account_id = fields.Many2one('account.account', string=u'-รับเงินขาด', required=False, readonly=False,
                                          related='company_id.get_paid_account_id')
    get_overgrown_account_id = fields.Many2one('account.account', string=u'+รับเงินเกิน', required=False,
                                               readonly=False,
                                               related='company_id.get_overgrown_account_id'
                                               )
    profit_loss_account_id = fields.Many2one('account.account', string=u'+,- กำไรขาดทุนอัตราแลกเปลี่ยน', required=False,
                                             readonly=False,
                                             related='company_id.profit_loss_account_id')
    fee_account_id = fields.Many2one('account.account', string=u'ค่าธรรมเนียม', required=False, readonly=False,
                                     related='company_id.fee_account_id')

    action_report_deposit_id = fields.Many2one('ir.actions.report', u'รูปแบบใบรับมัดจำ',
                                               related='company_id.action_report_deposit_id',
                                               copy=False)
