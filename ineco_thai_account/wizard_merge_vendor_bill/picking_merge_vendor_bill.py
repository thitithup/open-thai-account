# -*- coding: utf-8 -*-


from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, exceptions, _


class PickingMergeVendorBill(models.TransientModel):
    _name = "picking.merge.vendor.bill"
    _description = 'picking merge vendor bill'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    item_ids = fields.One2many('picking.merge.vendor.bill.line', 'order_id', string='Order Lines')
    partner_id = fields.Many2one('res.partner', string='Vendor', required=True, readonly=True, tracking=True)

    @api.model
    def default_get(self, fields):
        res = super(PickingMergeVendorBill, self).default_get(fields)
        ineco_picking_obj = self.env['stock.picking']
        line_ids = self.env.context.get('active_ids', False)
        pickings = ineco_picking_obj.browse(line_ids)
        items = []
        for picking in pickings:
            if picking.state != 'done':
                raise UserError(_('You cannot merge a picking.'))
            line_data_vals = {
                'name': picking.id,
                'partner_id': picking.partner_id.id}
            items.append([0, 0, line_data_vals])
        res['partner_id'] = pickings[0].partner_id.id
        res['item_ids'] = items
        return res

    def _prepare_vendor_bill(self, po_name, narration, order):
        self.ensure_one()
        move_type = 'in_invoice'
        journal = self.env['account.move'].with_context(default_move_type=move_type)._get_default_journal()
        if not journal:
            raise UserError(
                _('Please define an accounting sales journal for the company %s (%s).', order.company_id.name,
                  order.company_id.id))
        invoice_vals = {
            'ref': po_name or '',
            'move_type': move_type,
            'narration': narration or '',
            'currency_id': order.partner_id.property_product_pricelist.currency_id.id,
            'campaign_id': False,
            'medium_id': False,
            'source_id': False,
            'user_id': order.user_id.id,
            'invoice_user_id': order.user_id.id,
            'team_id': False,
            'partner_id': order.partner_id.id,
            'partner_shipping_id': order.partner_id.id,
            'fiscal_position_id': False,
            'partner_bank_id': order.company_id.partner_id.bank_ids[:1].id,
            'journal_id': journal.id,  # company comes from the journal
            'invoice_origin': order.name,
            'invoice_payment_term_id': False,
            'payment_reference': order.supplier_invoice_number,
            'invoice_date': order.supplier_invoice_date,
            'transaction_ids': False,
            'invoice_line_ids': [],
            'company_id': order.company_id.id,
            # 'man_transport_type': order.man_transport_type.id
        }
        return invoice_vals

    def _create_vendor_bill(self, po_name, narration):
        move_type = 'in_invoice'
        invoice_vals_list = []
        invoice_item_sequence = 0  # Incremental sequencing to keep the lines order on the invoice.
        for order in self.item_ids[0]:
            order = order.with_company(order.name.company_id)
            invoice_vals = self._prepare_vendor_bill(po_name, narration, order.name)
            invoice_line_vals = []
            picking_ids = [picking.name.id for picking in self.item_ids]
            stock_move_ids = self.env['stock.move'].search([('picking_id', 'in', picking_ids)])
            for line in stock_move_ids:
                invoice_item_sequence += 1
                invoice_line_vals.append(
                    (0, 0, line._prepare_invoice_line(
                        sequence=invoice_item_sequence,
                    )),
                )
            order.name.write({'merge_invoice': True})
            invoice_vals['invoice_line_ids'] += invoice_line_vals
            invoice_vals_list.append(invoice_vals)
        moves = self.env['account.move'].sudo().with_context(default_move_type=move_type).create(invoice_vals_list)
        return moves

    def action_invoice_create_vendor_bill(self):
        po_name = ''
        narration = ''
        for picking in self.item_ids:
            if picking.name.state == 'cancel':
                raise UserError(_('You cannot merge a cancelled picking.'))
            if not picking.name.is_create_invoice_vendor:
                raise UserError(_('You cannot merge a picking that is not create invoice vendor.'))

            if self.partner_id.id != picking.partner_id.id:
                raise UserError(_("You can not merge picking with different vendor."))
            if picking.origin:
                po_name += picking.origin + ','
                narration += str(picking.name.note) + ','

        invoice_id = self._create_vendor_bill(po_name, narration)
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


class PickingMergeVendorBillLine(models.TransientModel):
    _name = 'picking.merge.vendor.bill.line'
    _description = 'รายการรับสินค้า'
    _inherit = ['mail.thread']

    order_id = fields.Many2one('picking.merge.vendor.bill', string='Line', ondelete='cascade')
    name = fields.Many2one('stock.picking', string=u'Picking', required=False, copy=False, index=True,
                           tracking=True)
    partner_id = fields.Many2one('res.partner', string='Vendor', required=False, readonly=False,
                                 tracking=True)
    origin = fields.Char(string='Origin', related='name.origin', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting', 'Waiting Another Operation'),
        ('confirmed', 'Waiting'),
        ('assigned', 'Ready'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', related='name.state', readonly=True)
