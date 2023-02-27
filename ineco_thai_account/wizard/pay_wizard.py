# -*- coding: utf-8 -*-


from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, exceptions, _


class PayWizard(models.TransientModel):
    _name = "pay.wizard"
    _description = 'รับชำระ'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    item_ids = fields.One2many('pay.wizard.line', 'order_id', string='Order Lines')
    customer_id = fields.Many2one('res.partner', string='ลูกค้า', required=True, readonly=True, tracking=True)
    date = fields.Date(string=u'ลงวันที่', required=True, default=fields.Date.context_today,
                       tracking=True)
    date_due = fields.Date(string=u'วันที่รับเงิน', required=True, tracking=True)
    journal_id = fields.Many2one('account.journal', string=u'สมุดรายวันรับ', required=True)
    is_customer = fields.Boolean(default=False, string="ลูกหนี้")
    is_sup = fields.Boolean(default=False, string="เจ้าหนี้")

    company_id = fields.Many2one('res.company', string='Company', store=True, readonly=True, change_default=True,
                                 default=lambda self: self.env.company)

    @api.model
    def default_get(self, fields):
        res = super(PayWizard, self).default_get(fields)
        ineco_billing_obj = self.env['ineco.billing']
        line_ids = self.env.context.get('active_ids', False)
        billing = ineco_billing_obj.browse(line_ids)
        items = []

        for iv in billing.invoice_ids:
            amount_receipt = iv.amount_residual_signed
            if iv.move_type == 'in_invoice':
                amount_receipt = abs(iv.amount_residual_signed)
            if iv.amount_total_signed != 0.0:
                line_data_vals = {
                    'name': iv.id,
                    'date_invoice': iv.invoice_date,
                    'amount_total': iv.amount_total_signed,
                    'amount_residual': iv.amount_residual_signed,
                    'amount_receipt': amount_receipt,
                }
                items.append([0, 0, line_data_vals])

        for refund in billing.refund_ids:
            refund_amount_receipt = iv.amount_residual_signed
            if refund.move_type == 'in_refund':
                refund_amount_receipt = - abs(iv.amount_residual_signed)

            if refund.amount_total_signed != 0.0:
                line_data_vals = {
                    'name': refund.id,
                    'date_invoice': refund.invoice_date,
                    'amount_total': refund.amount_total_signed,
                    'amount_residual': refund.amount_residual_signed,
                    'amount_receipt': refund.amount_total_signed,
                }
                items.append([0, 0, line_data_vals])

        res['customer_id'] = billing.customer_id.id
        res['company_id'] = billing.company_id.id
        res['item_ids'] = items
        return res

    def action_create_cus_pay(self):
        ineco_billing_obj = self.env['ineco.billing']
        line_ids = self.env.context.get('active_ids', False)
        billing = ineco_billing_obj.browse(line_ids)
        payment = self.env['ineco.customer.payment']
        journal = self.journal_id
        if not journal:
            raise ValidationError(_('ไม่พบสมุดรายวันรับเงิน กรุณาสร้าง'))
        pml = []
        data = {
            'customer_id': self.customer_id.id,
            'date_due': self.date_due,
            'date': self.date,
            'journal_id': journal.id,
            'line_ids': []
        }
        for iv in self.item_ids:
            mvl = self.env['account.move.line'].search([
                ('move_id', '=', iv.name.id),
                ('account_id', '=', self.customer_id.property_account_receivable_id.id)
            ])

            line_data_vals = {
                'name': mvl.id,
                'amount_total': iv.name.amount_total_signed,
                'amount_residual': iv.name.amount_residual_signed,
                'amount_receipt': iv.amount_receipt
            }
            pml.append((0, 0, line_data_vals))
        payment_id = payment.create(data)
        payment_id.write({'line_ids': pml})
        billing.state = "done"
        view_ref = self.env['ir.model.data'].check_object_reference('ineco_thai_account',
                                                                    'view_ineco_customer_payment_form')
        view_id = view_ref and view_ref[1] or False,
        return {
            'type': 'ir.actions.act_window',
            'name': 'ineco.customer.payment.form',
            'res_model': 'ineco.customer.payment',
            'res_id': payment_id.id,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'current',
            'nodestroy': True,
        }

    def action_create_supplier_pay(self):
        ineco_billing_obj = self.env['ineco.billing']
        line_ids = self.env.context.get('active_ids', False)
        billing = ineco_billing_obj.browse(line_ids)
        payment = self.env['ineco.supplier.payment']
        journal = self.journal_id
        if not journal:
            raise ValidationError(_('ไม่พบสมุดรายวันจ่ายเงิน กรุณาสร้าง'))
        pml = []
        data = {
            'partner_id': self.customer_id.id,
            'date_due': self.date_due,
            'date': self.date,
            'journal_id': journal.id,
            'line_ids': []
        }
        for iv in self.item_ids:
            mvl = self.env['account.move.line'].search([
                ('move_id', '=', iv.name.id),
                ('account_id', '=', self.customer_id.property_account_payable_id.id),
                ('move_id.state', 'not in', ('draft', 'cancel'))
            ])
            if iv.name:
                if iv.name.move_type == 'in_invoice':
                    amount_total = abs(mvl.move_id.amount_total_signed)
                    amount_residual = abs(mvl.amount_residual)
                    amount_receipt = abs(iv.amount_receipt)
                elif iv.name.move_type == 'in_refund':
                    amount_total = - abs(mvl.move_id.amount_total_signed)
                    amount_residual = - abs(mvl.amount_residual)
                    amount_receipt = - abs(iv.amount_receipt)

            line_data_vals = {
                'name': mvl.id,
                'amount_total': amount_total,
                'amount_residual': amount_residual,
                'amount_receipt': amount_receipt
            }
            pml.append((0, 0, line_data_vals))
        payment_id = payment.create(data)
        payment_id.write({'line_ids': pml})
        billing.state = "done"
        view_ref = self.env['ir.model.data'].check_object_reference('ineco_thai_account',
                                                                    'view_ineco_supplier_payment_form')
        view_id = view_ref and view_ref[1] or False,
        return {
            'type': 'ir.actions.act_window',
            'name': 'ineco.supplier.payment.form',
            'res_model': 'ineco.supplier.payment',
            'res_id': payment_id.id,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'current',
            'nodestroy': True,
        }


class PayWizardLine(models.TransientModel):
    _name = 'pay.wizard.line'
    _description = 'รายการรับชำระ'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    order_id = fields.Many2one('pay.wizard', string='pay', ondelete='cascade')
    name = fields.Many2one('account.move', string=u'ใบแจ้งหนี้/ใบกำกับภาษี', required=True, copy=False, index=True,
                           tracking=True)
    date_invoice = fields.Date(string=u'ลงวันที่', )
    amount_total = fields.Float(string=u'ยอดตามบิล', )
    amount_residual = fields.Float(string=u'ยอดค้างชำระ', )
    amount_receipt = fields.Float(string=u'ยอดชำระ', copy=False, tracking=True)
