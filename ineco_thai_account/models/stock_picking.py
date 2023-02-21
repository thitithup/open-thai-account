# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.tools.float_utils import float_compare
from odoo.exceptions import AccessError, UserError, ValidationError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    is_create_invoice_vendor = fields.Boolean(string='Vender Invoice',
                                              related='picking_type_id.create_invoice_vendor',
                                              store=True)
    is_create_invoice_customer = fields.Boolean(string='Customer Invoice',
                                                related='picking_type_id.create_invoice_customer',
                                                store=True)
    invoice_id = fields.Many2one("account.move", string='Invoices', readonly=True, copy=False)
    supplier_invoice_number = fields.Char(string='Vendor Bill Number', copy=False, tracking=True)
    supplier_invoice_date = fields.Date(string="Vendor Bill Date", copy=False, tracking=True)
    merge_invoice = fields.Boolean(string="Merged Invoice", default=False)

    def _prepare_vendor_bill(self):
        """
        Prepare the dict of values to create the new invoice for a sales order. This method may be
        overridden to implement custom invoice generation (making sure to call super() to establish
        a clean extension chain).
        """
        self.ensure_one()
        move_type = 'in_invoice'

        journal = self.env['account.move'].with_context(default_move_type=move_type)._get_default_journal()
        if not journal:
            raise UserError(
                _('Please define an accounting purchase journal for the company %s (%s).', self.company_id.name,
                  self.company_id.id))

        # if not self.man_transport_type:
        #     raise UserError('กรุณาระบุผู้จัดส่งก่อน !!!')

        invoice_vals = {
            'ref': self.origin or '',
            'move_type': move_type,
            'narration': self.note,
            'currency_id': self.partner_id.property_product_pricelist.currency_id.id,
            'campaign_id': False,
            'medium_id': False,
            'source_id': False,
            'user_id': self.user_id.id,
            'invoice_user_id': self.user_id.id,
            'team_id': False,
            'partner_id': self.partner_id.id,
            'partner_shipping_id': self.partner_id.id,
            'fiscal_position_id': False,
            'partner_bank_id': self.company_id.partner_id.bank_ids[:1].id,
            'journal_id': journal.id,  # company comes from the journal
            'invoice_origin': self.name,
            'invoice_payment_term_id': False,
            'payment_reference': self.supplier_invoice_number,
            'invoice_date': self.supplier_invoice_date,
            'transaction_ids': False,
            'invoice_line_ids': [],
            'company_id': self.company_id.id,
        }
        return invoice_vals

    def _prepare_invoice(self):
        """
        Prepare the dict of values to create the new invoice for a sales order. This method may be
        overridden to implement custom invoice generation (making sure to call super() to establish
        a clean extension chain).
        """
        self.ensure_one()
        move_type = 'out_invoice'

        journal = self.env['account.move'].with_context(default_move_type=move_type)._get_default_journal()
        if not journal:
            raise UserError(
                _('Please define an accounting sales journal for the company %s (%s).', self.company_id.name,
                  self.company_id.id))

        # if not self.man_transport_type:
        #     raise UserError('กรุณาระบุผู้จัดส่งก่อน !!!')
        sale_order = False
        if self.origin:
            sale_order = self.env['sale.order'].sudo().search([('name', '=', self.origin)])
        invoice_vals = {
            'ref': self.origin or '',
            'move_type': move_type,
            'narration': self.note,
            'currency_id': self.partner_id.property_product_pricelist.currency_id.id,
            'campaign_id': False,
            'medium_id': False,
            'source_id': False,
            'user_id': sale_order and sale_order.user_id.id,
            'invoice_user_id': self.env.user.id,
            'team_id': False,
            'partner_id': self.partner_id.id,
            'partner_shipping_id': self.partner_id.id,
            'fiscal_position_id': False,
            'partner_bank_id': self.company_id.partner_id.bank_ids[:1].id,
            'journal_id': journal.id,  # company comes from the journal
            'invoice_origin': self.name,
            'invoice_payment_term_id': False,
            'payment_reference': False,
            'invoice_date': False,
            'transaction_ids': False,
            'invoice_line_ids': [],
            'company_id': self.company_id.id,
            'sale_no': sale_order or False
        }
        return invoice_vals

    def _create_vendor_bill(self, grouped=False, final=False, date=None):
        move_type = 'in_invoice'
        # 1) Create invoices.
        invoice_vals_list = []
        invoice_item_sequence = 0  # Incremental sequencing to keep the lines order on the invoice.
        for order in self:
            order = order.with_company(order.company_id)
            invoice_vals = order._prepare_vendor_bill()
            invoice_line_vals = []
            for line in self.move_lines:
                invoice_item_sequence += 1
                invoice_line_vals.append(
                    (0, 0, line._prepare_invoice_line(
                        sequence=invoice_item_sequence,
                    )),
                )

            invoice_vals['invoice_line_ids'] += invoice_line_vals
            invoice_vals_list.append(invoice_vals)
        moves = self.env['account.move'].sudo().with_context(default_move_type=move_type).create(invoice_vals_list)
        self.invoice_id = moves.id
        return moves

    def action_invoice_create_vendor_bill(self):
        if self:
            invoice_id = self._create_vendor_bill()
            view_ref = self.env['ir.model.data'].check_object_reference('account',
                                                                        'view_move_form')
            view_id = view_ref and view_ref[1] or False,
            if view_ref:
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'ineco.account.move.form',
                    'res_model': 'account.move',
                    'res_id': invoice_id.id,
                    'view_type': 'form',
                    'view_mode': 'form',
                    'view_id': view_id,
                    'target': 'current',
                    'nodestroy': True,
                }
            return {'type': 'ir.actions.act_window_close'}

    def _create_invoices(self, grouped=False, final=False, date=None):
        # 1) Create invoices.
        invoice_vals_list = []
        invoice_item_sequence = 0  # Incremental sequencing to keep the lines order on the invoice.
        for order in self:
            order = order.with_company(order.company_id)
            invoice_vals = order._prepare_invoice()
            invoice_line_vals = []
            for line in self.move_lines:
                invoice_item_sequence += 1
                invoice_line_vals.append(
                    (0, 0, line._prepare_invoice_line(
                        sequence=invoice_item_sequence,
                    )),
                )

            invoice_vals['invoice_line_ids'] += invoice_line_vals
            invoice_vals_list.append(invoice_vals)
        moves = self.env['account.move'].sudo().with_context(default_move_type='out_invoice').create(
            invoice_vals_list)
        self.invoice_id = moves.id
        return moves

    def action_invoice_create(self):
        if self:
            invoice_id = self._create_invoices()
            view_ref = self.env['ir.model.data'].check_object_reference('account',
                                                                        'view_move_form')
            view_id = view_ref and view_ref[1] or False,
            if view_ref:
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'ineco.account.move.form',
                    'res_model': 'account.move',
                    'res_id': invoice_id.id,
                    'view_type': 'form',
                    'view_mode': 'form',
                    'view_id': view_id,
                    'target': 'current',
                    'nodestroy': True,
                }


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _prepare_invoice_line(self, **optional_values):
        self.ensure_one()
        aml_currency = self.purchase_line_id.currency_id
        date = fields.Date.today()
        if self.picking_id.is_create_invoice_vendor:
            res = {
                'display_type': False,
                'sequence': self.sequence,
                'name': self.name,
                # 'account_id': self.product_id.property_account_income_id.id,
                'product_id': self.product_id.id,
                'product_uom_id': self.product_uom.id,
                'quantity': self.product_uom_qty,
                # 'price_unit': self.purchase_line_id.price_unit,
                'price_unit': self.purchase_line_id.currency_id._convert(self.purchase_line_id.price_unit, aml_currency,
                                                                         self.purchase_line_id.company_id, date,
                                                                         round=False),
                'tax_ids': [(6, 0, self.purchase_line_id.taxes_id.ids)],
                'analytic_account_id': self.purchase_line_id.account_analytic_id.id,
                'analytic_tag_ids': [(6, 0, self.purchase_line_id.analytic_tag_ids.ids)],
                'sale_line_ids': False,
                'purchase_line_id': self.purchase_line_id.id,
            }
        else:
            res = {
                'display_type': False,
                'sequence': self.sequence,
                'name': self.name,
                # 'account_id': self.product_id.property_account_income_id.id,
                'product_id': self.product_id.id,
                'product_uom_id': self.product_uom.id,
                'quantity': self.product_uom_qty,
                'discount': self.sale_line_id.discount,
                'price_unit': self.sale_line_id.price_unit,
                'tax_ids': [(6, 0, self.sale_line_id.tax_id.ids)],
                'analytic_tag_ids': [(6, 0, self.sale_line_id.analytic_tag_ids.ids)],
                'sale_line_ids': False,
            }
            if self.sale_line_id:
                res['sale_line_ids'] = [(4, self.sale_line_id.id)]
        return res
