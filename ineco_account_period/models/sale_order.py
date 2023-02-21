# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools
from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta


class SaleOrdre(models.Model):
    _inherit = 'sale.order'

    def action_cancel(self):
        cancel_warning = self._show_cancel_wizard()
        if cancel_warning:
            return {
                'name': _('Cancel Sales Order'),
                'view_mode': 'form',
                'res_model': 'sale.order.cancel',
                'view_id': self.env.ref('sale.sale_order_cancel_view_form').id,
                'type': 'ir.actions.act_window',
                'context': {'default_order_id': self.id},
                'target': 'new'
            }
        inv = self.invoice_ids.filtered(lambda inv: inv.state == 'draft')
        if inv:
            inv.button_cancel()
        return self.write({'state': 'cancel'})