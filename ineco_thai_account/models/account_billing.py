# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class InecoBilling(models.Model):

    @api.depends('name', 'date', 'date_due', 'customer_id')
    def _get_amount(self):
        out_invoice = 0.00
        out_refund = 0.00
        for invoice in self.invoice_ids:
            out_invoice += invoice.amount_residual
        for invoice in self.refund_ids:
            out_refund -= invoice.amount_residual
        self.amount_residual = out_invoice
        self.amount_refund = out_refund
        self.amount_billing = out_invoice + out_refund

    _name = 'ineco.billing'
    _description = 'Billing'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    type_vat = fields.Selection([('a', u'1'), ('b', u'2'), ], string=u'ประเภทภาษี')
    type = fields.Selection([('ar', u'ลูกหนี้'), ('ap', u'เจ้าหนี้'), ], string=u'ประเภทกิจกรรม')
    name = fields.Char(string='เลขที่ใบวางบิล', size=32, copy=False, tracking=True)
    date = fields.Date(string='ลงวันที่', required=True, default=fields.Date.context_today, tracking=True)
    date_due = fields.Date(string='กำหนดชำระ', required=True, tracking=True)
    customer_id = fields.Many2one('res.partner', string='ลูกค้า', required=True, tracking=True)
    note = fields.Text(string='หมายเหตุ', tracking=True)
    invoice_ids = fields.Many2many('account.move',
                                   'billing_invoice_rel',
                                   'billing_id',
                                   'invoice_id',
                                   string='ใบแจ้งหนี้/ใบกำกับภาษี')
    refund_ids = fields.Many2many('account.move',
                                  'billing_invoice_refund_rel',
                                  'billing_id',
                                  'invoice_id',
                                  string='ใบลดหนี้')
    amount_residual = fields.Float(compute='_get_amount', string='ยอดหนี้คงค้าง', digits=(12, 2), store=True)
    amount_refund = fields.Float(compute='_get_amount', string='ยอดลดหนี้', digits=(12, 2), store=True)
    amount_billing = fields.Float(compute='_get_amount', string='รวมเป็นเงิน', digits=(12, 2), store=True)
    change_number = fields.Boolean(string='เปลี่ยนเลขใบวางบิล', )

    state = fields.Selection([('draft', 'Draft'), ('post', 'Posted'), ('done', 'Done')],
                             string=u'State', default='draft')

    is_locked = fields.Boolean(default=True, help='When the picking is not done this allows changing the '
                                                  'initial demand. When the picking is done this allows '
                                                  'changing the done quantities.')
    payment = fields.Many2one('ineco.customer.payment', string=u'เลขรับชำระ')

    company_id = fields.Many2one('res.company',string='Company', store=True, readonly=True,change_default=True,
                                 default=lambda self: self.env.company)

    def Select_all_pay(self):
        for iv in self.invoice_ids:
            iv.SelectPay()
        for refund in self.refund_ids:
            refund.SelectPay()

    def UpDateDone(self):
        self._get_amount()
        if self.amount_residual == 0.0:
            self.write({'state': 'done'})

    @api.onchange('type_vat', 'customer_id')
    def onchange_type_vat(self):
        self.invoice_ids = False
        self.refund_ids = False

    def action_toggle_is_locked(self):
        self.ensure_one()
        self.is_locked = not self.is_locked
        return True

    _sql_constraints = [
        ('name', 'unique( name )', 'เลขที่วางบิลห้ามซ้ำ.')
    ]

    def updateInvoice(self):
        for billing in self:
            for invoice in billing.invoice_ids:
                update_sql = """
                    update account_move
                    set billing_id = %s
                    where id = %s 
                """ % (billing.id, invoice.id)
                self._cr.execute(update_sql)
            for refund in billing.refund_ids:
                update_sql = """
                    update account_move
                    set billing_id = %s
                    where id = %s 
                """ % (billing.id, refund.id)
                self._cr.execute(update_sql)

    def clearInvoice(self):
        for billing in self:
            sql = """
                update account_move
                set billing_id = null
                where billing_id = %s
            """ % (billing.id)
            self._cr.execute(sql)

    def write(self, vals):
        self.clearInvoice()
        res = super(InecoBilling, self).write(vals)
        self.updateInvoice()
        return res

    def action_post(self):
        if self.name == False:
            self.name = self.env['ir.sequence'].next_by_code('ineco.billing')
        self.write({'state': 'post'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_create_cus_pay(self):
        payment = self.env['ineco.customer.payment']
        journal = self.env['account.journal'].search([('type', '=', 'receive'), ('type_vat', '=', self.type_vat)],
                                                     limit=1)
        pml = []
        data = {
            'customer_id': self.customer_id.id,
            'date_due': self.date_due,
            'journal_id': journal.id,
            'line_ids': []
        }
        for iv in self.invoice_ids:
            line_data_vals = {
                # 'payment_id': payment_id.id,
                'name': iv.id,
                'amount_total': iv.amount_total,
                'amount_residual': iv.residual,
                'amount_receipt': iv.amount_total
            }
            pml.append((0, 0, line_data_vals))

        for refund in self.refund_ids:
            line_data_vals = {
                # 'payment_id': refund.id,
                'name': refund.id,
                'amount_total': iv.amount_total,
                'amount_residual': iv.residual,
                'amount_receipt': iv.amount_total
            }
            pml.append((0, 0, line_data_vals))
        payment_id = payment.create(data)
        payment_id.sudo().write({'line_ids': pml})
        self.write({'state': 'done', 'payment': payment_id.id})
        return payment_id

    @api.model
    def create(self, vals):
        bill_id = super(InecoBilling, self.with_context(mail_create_nosubscribe=True)).create(vals)
        bill_id.updateInvoice()
        return bill_id
