# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError


class AccountMoveReversal(models.TransientModel):
    """Credit Notes"""

    _inherit = "account.move.reversal"

    @api.depends('company_id', 'move_type')
    def _compute_suitable_journal_ids(self):
        for m in self:
            if m.move_type == 'out_invoice':
                journal_type = 'sale'
            elif m.move_type == 'in_invoice':
                journal_type = 'purchase'
            domain = [('company_id', '=', m.company_id.id), ('type', '=', journal_type),('is_refund','=',True)]
            m.suitable_journal_ids = self.env['account.journal'].search(domain)

    ineco_filter_refund = fields.Selection(
        [('refund', u'เก็บไว้หักตอนรับชำระหนี้'), ('cancel', u'หักกับใบกำกับที่อ้างอิง')],
        default='refund', string='Refund Method', required=True,
        help='Refund base on this type. You can not Modify and Cancel if the invoice is already reconciled')

    journal_id = fields.Many2one('account.journal', string='Use Specific Journal',
                                 help='If empty, uses the journal of the journal entry to be reversed.',
                                 check_company=True,domain="[('id', 'in', suitable_journal_ids)]")
    suitable_journal_ids = fields.Many2many('account.journal', compute='_compute_suitable_journal_ids')

    def reverse_moves(self):
        self.ensure_one()
        moves = self.move_ids

        # Create default values.
        default_values_list = []
        for move in moves:
            default_values_list.append(self._prepare_default_reversal(move))

        batches = [
            [self.env['account.move'], [], True],   # Moves to be cancelled by the reverses.
            [self.env['account.move'], [], False],  # Others.
        ]
        for move, default_vals in zip(moves, default_values_list):
            is_auto_post = bool(default_vals.get('auto_post'))
            is_cancel_needed = not is_auto_post and self.ineco_filter_refund in ('cancel')
            batch_index = 0 if is_cancel_needed else 1
            batches[batch_index][0] |= move
            batches[batch_index][1].append(default_vals)

        # Handle reverse method.
        moves_to_redirect = self.env['account.move']
        for moves, default_values_list, is_cancel_needed in batches:
            new_moves = moves._reverse_moves(default_values_list, cancel=is_cancel_needed)

            if self.refund_method == 'modify':
                moves_vals_list = []
                for move in moves.with_context(include_business_fields=True):
                    moves_vals_list.append(move.copy_data({'date': self.date if self.date_mode == 'custom' else move.date})[0])
                new_moves = self.env['account.move'].create(moves_vals_list)

            moves_to_redirect |= new_moves

        self.new_move_ids = moves_to_redirect

        # Create action.
        action = {
            'name': _('Reverse Moves'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
        }
        if len(moves_to_redirect) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': moves_to_redirect.id,
            })
        else:
            action.update({
                'view_mode': 'tree,form',
                'domain': [('id', 'in', moves_to_redirect.ids)],
            })
        return action


class AccountDebitNote(models.TransientModel):
    """Credit Notes"""

    _inherit = "account.debit.note"

    suitable_journal_ids = fields.Many2many('account.journal', compute='_compute_suitable_journal_ids')

    @api.depends('move_ids')
    def _compute_suitable_journal_ids(self):
        for record in self:
            move_ids = record.move_ids
            record.move_type = move_ids[0].move_type if len(move_ids) == 1 or not any(
                m.move_type != move_ids[0].move_type for m in move_ids) else False
            for m in self:
                if m.move_type == 'out_invoice':
                    journal_type = 'sale'
                elif m.move_type == 'in_invoice':
                    journal_type = 'purchase'
                domain = [('type', '=', journal_type), ('is_add_dn', '=', True)]
                m.suitable_journal_ids = self.env['account.journal'].search(domain)