# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class InecoAccountVat(models.Model):
    _name = "ineco.account.vat"
    _description = "Vat"

    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if self.partner_id:
            self.taxid = self.partner_id.vat or ''
            self.depcod = self.partner_id.branch_no or ''

    move_line_id = fields.Many2one('account.move.line', string='Move Line', ondelete="restrict")
    account_id = fields.Many2one('account.account', string='Account')
    customer_payment_id = fields.Many2one('ineco.customer.payment', string='Customer Payment', ondelete="restrict")
    customer_deposit_id = fields.Many2one('ineco.customer.deposit', string='Customer Deposit', ondelete="restrict")
    supplier_payment_id = fields.Many2one('ineco.supplier.payment', string='Supplier Payment', ondelete="restrict")
    supplier_deposit_id = fields.Many2one('ineco.supplier.deposit', string='Supplier Deposit', ondelete="restrict")
    invoice_id = fields.Many2one('account.move', string='Invoice', ondelete="restrict")

    name = fields.Char(string='เลขที่ใบกำกับภาษี',
                       required=False, copy=False, tracking=True)
    docdat = fields.Date(string='ลงวันที่', required=True, tracking=True)
    vatprd = fields.Date(string='วันที่ยื่นภาษี')
    partner_id = fields.Many2one('res.partner', 'พาร์ทเนอร์', required=False)
    partner_name = fields.Char(string=u'ผู้จำหน่าย', required=False, copy=True)
    taxid = fields.Char(string='เลขประจำตัวผู้เสียภาษี', required=True, copy=True)
    depcod = fields.Char(string='รหัสสาขา', size=5, required=True, copy=True)

    period_id = fields.Many2one('ineco.account.period',string=u'งวดที่', copy=False,store=True)
    period_type_id = fields.Many2one('ineco.account.fiscalyear', string=u'ปี', related='period_id.fiscalyear_id',
                                     store=True)

    amount_untaxed = fields.Float(string='ยอดก่อนภาษี')
    amount_tax = fields.Float(string='ภาษี')
    amount_total = fields.Float(string='ยอดเงินรวม')
    late = fields.Boolean(string='ยื่นล่าช้า')
    remark = fields.Char(string='หมายเหตุ', size=30)

    tax_sale_ok = fields.Boolean(string=u'Sale Tax', copy=False, related='account_id.tax_sale_ok',
                                 tracking=True, store=True)

    tax_sale_wait_ok = fields.Boolean(string=u'Sale Tax wait', copy=False, related='account_id.tax_sale_wait',
                                          tracking=True, store=True)


    tax_purchase_ok = fields.Boolean(string=u'Purchase Tax', copy=False, related='account_id.tax_purchase_ok',
                                     tracking=True, store=True)
    tax_purchase_wait_ok = fields.Boolean(string=u'Purchase Tax wait', copy=False, related='account_id.wait',
                                          tracking=True, store=True)
    vat_type = fields.Selection([('sale', u'ภาษีขาย'),
                                 ('purchase', u'ภาษีซื้อ')],
                                string=u'ประเภทภาษี', tracking=True)

    reconciliation_in = fields.Many2one('ineco.account.vat', string=u'กลับภาษีซื้อ')
    move_id = fields.Many2one('account.move', string=u'เล่มกลับ')


    vatrec = fields.Char(string='vatrec', size=1)
    vattyp = fields.Char(string='vattyp', size=1)
    rectyp = fields.Char(string='rectyp', size=1)
    # period_id = fields.Many2one('ineco.account.period', string='งวดภาษี', required=True)
    refnum = fields.Char(string='refnum', size=15)
    newnum = fields.Char(string='newnum', size=10)
    descrp = fields.Char(string='descrp', size=60)
    amt01 = fields.Float(string='amt01', digits=(8, 2))
    vat01 = fields.Float(string='vat01', digits=(8, 2))
    amt02 = fields.Float(string='รายได้จากการขาย', digits=(8, 2))
    vat02 = fields.Float(string='จำนวนภาษีมูลค่าเพิ่ม', digits=(8, 2))
    amtrat0 = fields.Float(string='amtrat0', digits=(8, 2))
    self_added = fields.Char(string='self_added', size=1)
    had_modify = fields.Char(string='had_modify', size=1)
    docstat = fields.Char(string='docstat', size=1)
    orgnum = fields.Integer(string='orgnum')
    prenam = fields.Char(string='prenam', size=15)

    customer_deposit_line_id = fields.Many2one('ineco.customer.deposit.line', string='Customer Deposit line')
    supplier_deposit_line_id = fields.Many2one('ineco.supplier.deposit.line', string='Supplier Deposit line')
    company_id = fields.Many2one('res.company', string='Company', store=True, readonly=True, change_default=True,
                                 default=lambda self: self.env.company)

    def write(self, vals):
        res = super(InecoAccountVat, self).write(vals)
        vstr = ''
        if self.tax_purchase_ok:
            vstr = 'ภาษีซื้อ'
        if self.tax_purchase_wait_ok:
            vstr = 'ภาษีซื้อพัก'
        if self.invoice_id:
            self.invoice_id.message_post(body=_(
                f'เปลี่ยนแปลง ประเภท {vstr} ใบกำกับ {self.name} '
                f'วันที่ {self.docdat} วันที่ยื่น {self.vatprd} '
                f'ผู้จำหน่าย {self.partner_name} \n'
                f'เลขประจำตัวผู้เสียภาษี {self.taxid} รหัสสาขา {self.depcod} '
                f' ยอดก่อนภาษี {self.amount_untaxed} ภาษี {self.amount_tax}  ยอดเงินรวม {self.amount_total}'))

        return res

    @api.onchange('amount_untaxed', 'amount_tax')
    def onchange_amount_untaxed_and_tax(self):
        if self.amount_untaxed:
            self.amount_total = self.amount_untaxed + self.amount_tax

    @api.onchange('docdat', 'vatprd')
    def onchange_period_id(self):
        if self.vatprd and self.docdat:
            range_obj = self.env['ineco.account.period'].search([('date_start', '<=', self.vatprd),
                                                                 ('date_finish', '>', self.vatprd),
                                                                 ('company_id', '=', self.env.company.id),
                                                                 ])
        else:
            range_obj = self.env['ineco.account.period'].search([('date_start', '<=', self.docdat),
                                                                 ('date_finish', '>', self.docdat),
                                                                 ('company_id', '=', self.env.company.id),
                                                                 ])
        if range_obj:
            self.period_id = range_obj.id

    def _ineco_create_vat(self, line=False, inv=False, vatprd=False, period_id=False, signed=False, vat_type=False,
                          account_id=False):
        if line:
            mvl = line.id
            account_id = line.account_id.id
        else:
            mvl = False

        if vatprd:
            vatprd = vatprd
        else:
            vatprd = False

        new_data = {
            'move_line_id': mvl,
            'account_id': account_id,
            'name': inv.reference or '',
            'docdat': inv.date_invoice,
            'vatprd': vatprd,
            'period_id': period_id,
            'partner_id': inv.partner_id.id,
            'partner_name': inv.partner_id.name,
            'taxid': inv.partner_id.vat or '',
            'depcod': inv.partner_id.branch_no or '',
            'amount_untaxed': inv.amount_untaxed_signed,
            'amount_tax': inv.amount_tax * signed,
            'amount_total': inv.amount_total_signed,
            'invoice_id': inv.id,
            'vat_type': vat_type, }
        vat = self.create(new_data)
        return vat

    def unlink(self):
        for vat in self:
            if vat.tax_purchase_wait_ok and vat.move_id:
                raise ValidationError(_('ไม่สามารถลบได้เนื่องจากมีการกลับภาษีเพื่อนำส่งแล้ว {}'.format(self.move_id.name)))
            tax_break = self.env['ineco.account.vat'].search(
                [('reconciliation_in', '=', vat.id)])
            if tax_break:
                for line in tax_break:
                    line.write({'vatprd': False, 'reconciliation_in': False})

        return super(InecoAccountVat, self).unlink()
