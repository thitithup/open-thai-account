# -*- coding: utf-8 -*-


from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, exceptions, _


class SaleWizardDeposit(models.TransientModel):
    _name = "sale.wizard.deposit"
    _description = 'มัดจำขาย'
    _inherit = ['mail.thread']

    date = fields.Date(string=u'ลงวันที่', required=True, default=fields.Date.context_today,
                       tracking=True)
    name = fields.Text(string=u'คำอธิบาย', required=True, index=True, copy=False, tracking=True)
    tax_type = fields.Selection(default='percent', string="ประเภทภาษี", required=True,
                                selection=[('percent', 'ภาษีแยก'),
                                           ('included', u'ภาษีรวม')])
    default_amount = fields.Float(string=u'ยอดหนี้', copy=False, tracking=True)
    is_percent = fields.Boolean(u'กำหนดเปอร์เซ็นต์')
    percent_amount = fields.Float(string=u'เปอร์เซ็นต์', copy=False, tracking=True)



    amount_type_tax = fields.Float(required=True, digits=(16, 0), default=7, string='อัตราภาษี')
    amount_receipt = fields.Float(string=u'ยอดชำระ', copy=False, tracking=True,compute='_get_receipts')
    amount_untaxed = fields.Float(string='ยอดก่อนภาษี',required=True)
    amount_tax = fields.Float(string='ภาษี',compute='_get_receipts')

    image = fields.Image("Image", max_width=1920, max_height=1920,required=False)

    @api.onchange("is_percent","default_amount","percent_amount","amount_untaxed")
    def get_percent(self):
        if self.is_percent:
            amount = self.default_amount * self.percent_amount / 100
            self.amount_untaxed = amount


    @api.model
    def default_get(self, fields):
        res = super(SaleWizardDeposit, self).default_get(fields)
        sale_order_obj = self.env['sale.order']
        ids = self.env.context.get('active_ids', False)
        sale_order = sale_order_obj.browse(ids)
        res['default_amount'] = sale_order.amount_untaxed
        res['name'] = "เงินมัดจำ"
        return res

    @api.depends('tax_type','amount_type_tax','amount_untaxed')
    def _get_receipts(self):
        for receipt in self:
            untaxed = 0.0
            tax = 0.0
            if receipt.tax_type == 'percent':
                tax = receipt.amount_untaxed * receipt.amount_type_tax / 100
                receipt.amount_tax = tax
                receipt.amount_receipt = receipt.amount_untaxed + tax
            else:
                tax = receipt.amount_untaxed - (receipt.amount_untaxed * 100) / (100 + receipt.amount_type_tax)
                receipt.amount_tax = tax
                receipt.amount_receipt = receipt.amount_untaxed - tax


    def action_create_deposit(self):
        if self.amount_untaxed <= 0:
            raise UserError(("จำนวนไม่เข้าเงื่อนไข"))
        sale_order_obj = self.env['sale.order']
        line_ids = self.env.context.get('active_ids', False)
        sale_id = sale_order_obj.browse(line_ids)
        journal = self.env['account.journal'].search([('type','=','receive'),
                                                      ('is_deposit','=',True),
                                                      ('company_id','=',sale_id.company_id.id)])
        iml = []
        line = {
            'name':self.name,
            'amount_receipt':self.amount_receipt,
            'amount_untaxed': self.amount_untaxed,
            'amount_tax':self.amount_tax
        }
        iml.append((0, 0, line))
        date = {
            'journal_id':journal.id,
            'sale_order_id': sale_id.id,
            'customer_id':sale_id.partner_invoice_id.id,
            'date': self.date,
            'date_due':self.date,
            'type_deposit':'in',
            'tax_type': self.tax_type,
            'amount_type_tax':self.amount_type_tax,
            'image':self.image,
            'line_ids':iml
        }
        deposit = self.env['ineco.customer.deposit'].create(date)
        # sale_id.write({'deposit_id':deposit.id})



