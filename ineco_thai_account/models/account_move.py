# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
from odoo.tools import float_compare, date_utils, email_split, email_re
from odoo.tools.misc import formatLang, format_date, get_lang

from datetime import date, timedelta
from collections import defaultdict


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_starting_sequence(self):
        self.ensure_one()
        starting_sequence = "%s%04d%02d-00000" % (self.journal_id.code, self.date.year, self.date.month)
        if self.journal_id.refund_sequence and self.move_type in ('out_refund', 'in_refund'):
            starting_sequence = "R" + starting_sequence
        return starting_sequence

    @api.depends('state', 'move_type', 'company_id')
    def _compute_suitable_partner_ids(self):
        for m in self:
            if m.move_type in ['out_refund', 'out_invoice', 'out_receipt']:
                domain = [('is_company', '=', True), ('customer', '=', True), ('company_id', '=', m.company_id.id)]
            elif m.move_type in ['out_invoice', 'in_invoice', 'in_receipt']:
                domain = [('supplier', '=', True), ('is_company', '=', True), ('company_id', '=', m.company_id.id)]
            else:
                domain = [('is_company', '=', True), ('company_id', '=', m.company_id.id)]
            m.suitable_partner_ids = self.env['res.partner'].search(domain)

    suitable_partner_ids = fields.Many2many('res.partner', compute='_compute_suitable_partner_ids')
    partner_id = fields.Many2one('res.partner', readonly=True, tracking=True,
                                 states={'draft': [('readonly', False)]},
                                 check_company=True,
                                 domain="[('id', 'in', suitable_partner_ids)]",
                                 string='Partner', change_default=True)
    payment_ids = fields.One2many('ineco.customer.payment', 'move_id', string=u'รับชำระ', tracking=True)
    deposit_ids = fields.One2many('ineco.customer.deposit', 'move_id', string=u'รับมัดจำ', tracking=True)
    date_due = fields.Date(string=u'วันที่รับเงิน', tracking=True)
    detail = fields.Char(related='line_ids.name', string=u'รายละเอียด')

    billing_invoice_ids = fields.Many2many('ineco.billing',
                                           'billing_invoice_verder_rel',
                                           'invoice_id',
                                           'billing_id',

                                           string='ใบแจ้งหนี้/ใบกำกับภาษี')
    billing_refund_ids = fields.Many2many('ineco.billing',
                                          'billing_invoice_refund_verder_rel',
                                          'invoice_id',
                                          'billing_id',
                                          string='ใบลดหนี้')
    move_type_thai = fields.Selection(selection=[
        ('sale', 'Sale'),
        ('purchase', 'Purchase'),
        ('receive', 'Receivable'),  # New
        ('pay', 'Payable'),  # New
        ('general', 'Miscellaneous'),
    ], string='move_type_thai', required=False, store=True, index=True, readonly=True, tracking=True,
        change_default=True)

    @api.depends('company_id', 'invoice_filter_type_domain')
    def _compute_suitable_journal_ids(self):
        for m in self:
            if m.invoice_filter_type_domain:
                journal_type = m.invoice_filter_type_domain
                m.move_type_thai = journal_type
            else:
                journal_type = m.move_type_thai
            domain = [('company_id', '=', m.company_id.id), ('type', '=', journal_type)]
            m.suitable_journal_ids = self.env['account.journal'].search(domain)

    def button_cancel_input(self):
        self.button_cancel()
        for line in self.line_ids:
            line.ineco_vat.write({'vatprd': False})
            line.invoice_id.write({'ineco_reconciled_tax': False})

        self.unlink()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def update_move_foreign(self):
        iml = []
        move_data_vals = {
            'debit': 0.0,
            'credit': abs(1),
            'account_id': 1,
            'name': 'ส่วนต่าง',
        }
        iml.append((0, 0, move_data_vals))

        move_data_vals = {
            'debit': abs(1),
            'credit': 0.0,
            'account_id': 1,
            'name': 'ส่วนต่าง',
            # 'invoice_id': self.id
        }
        iml.append((0, 0, move_data_vals))

        self.move_id.sudo().write({'line_ids': iml})

    def _post_validate(self):
        res = super(AccountMove, self)._post_validate()
        for move in self:
            if move.line_ids:
                for line in move.line_ids:
                    if line.tax_ok:
                        total_vat = max(line.debit, line.credit)
                        check_vat = 0.0
                        if not (line.move_id.payment_ids or line.move_id.deposit_ids) and line.vat_ids:
                            for vat in line.vat_ids:
                                check_vat += abs(vat.amount_tax)
                            if round(total_vat, 2) != round(check_vat, 2):
                                raise UserError(u'ยอดภาษีไม่ตรง หรือยังคีย์ไม่ครบ')
                    if line.wht_ok:
                        total_wht = max(line.debit, line.credit)
                        check_wht = 0.0
                        if not (line.move_id.payment_ids or line.move_id.deposit_ids) and line.wht_ids:
                            for vat in line.wht_ids:
                                check_wht += vat.tax
                            if round(total_wht, 2) != round(check_wht, 2):
                                raise UserError(u'ยอดภาษีหัก ณ ที่จ่ายไม่ตรง หรือยังคีย์ไม่ครบ')
                    if line.cheque_ids:
                        total_cheque = max(line.debit, line.credit)
                        check_cheque = 0.0
                        if not line.move_id.payment_ids or line.move_id.deposit_ids:
                            for vat in line.cheque_ids:
                                check_cheque += vat.amount
                            if total_cheque != check_cheque:
                                raise UserError(u'ยอดเช็คไม่ตรง หรือยังคีย์ไม่ครบ')
        return res

    def _recompute_payment_terms_lines(self):
        ''' Compute the dynamic payment term lines of the journal entry.'''
        self.ensure_one()
        self = self.with_company(self.company_id)
        in_draft_mode = self != self._origin
        today = fields.Date.context_today(self)
        self = self.with_company(self.journal_id.company_id)

        def _get_payment_terms_computation_date(self):
            ''' Get the date from invoice that will be used to compute the payment terms.
            :param self:    The current account.move record.
            :return:        A datetime.date object.
            '''
            if self.invoice_payment_term_id:
                return self.invoice_date or today
            else:
                return self.invoice_date_due or self.invoice_date or today

        def _get_payment_terms_account(self, payment_terms_lines):
            ''' Get the account from invoice that will be set as receivable / payable account.
            :param self:                    The current account.move record.
            :param payment_terms_lines:     The current payment terms lines.
            :return:                        An account.account record.
            '''
            if payment_terms_lines:
                # Retrieve account from previous payment terms lines in order to allow the user to set a custom one.
                return payment_terms_lines[0].account_id
            elif self.partner_id:
                # Retrieve account from partner.
                if self.is_sale_document(include_receipts=True):
                    return self.partner_id.property_account_receivable_id
                else:
                    return self.partner_id.property_account_payable_id
            else:
                # Search new account.
                domain = [
                    ('company_id', '=', self.company_id.id),
                    ('internal_type', '=',
                     'receivable' if self.move_type in ('out_invoice', 'out_refund', 'out_receipt') else 'payable'),
                ]
                return self.env['account.account'].search(domain, limit=1)

        def _compute_payment_terms(self, date, total_balance, total_amount_currency):
            ''' Compute the payment terms.
            :param self:                    The current account.move record.
            :param date:                    The date computed by '_get_payment_terms_computation_date'.
            :param total_balance:           The invoice's total in company's currency.
            :param total_amount_currency:   The invoice's total in invoice's currency.
            :return:                        A list <to_pay_company_currency, to_pay_invoice_currency, due_date>.
            '''
            if self.invoice_payment_term_id:
                to_compute = self.invoice_payment_term_id.compute(total_balance, date_ref=date,
                                                                  currency=self.currency_id)
                if self.currency_id == self.company_id.currency_id:
                    # Single-currency.
                    return [(b[0], b[1], b[1]) for b in to_compute]
                else:
                    # Multi-currencies.
                    to_compute_currency = self.invoice_payment_term_id.compute(total_amount_currency, date_ref=date,
                                                                               currency=self.currency_id)
                    return [(b[0], b[1], ac[1]) for b, ac in zip(to_compute, to_compute_currency)]
            else:
                return [(fields.Date.to_string(date), total_balance, total_amount_currency)]

        def _compute_diff_payment_terms_lines(self, existing_terms_lines, account, to_compute):
            ''' Process the result of the '_compute_payment_terms' method and creates/updates corresponding invoice lines.
            :param self:                    The current account.move record.
            :param existing_terms_lines:    The current payment terms lines.
            :param account:                 The account.account record returned by '_get_payment_terms_account'.
            :param to_compute:              The list returned by '_compute_payment_terms'.
            '''
            # As we try to update existing lines, sort them by due date.
            existing_terms_lines = existing_terms_lines.sorted(lambda line: line.date_maturity or today)
            existing_terms_lines_index = 0

            # Recompute amls: update existing line or create new one for each payment term.
            new_terms_lines = self.env['account.move.line']
            for date_maturity, balance, amount_currency in to_compute:
                if self.journal_id.company_id.currency_id.is_zero(balance) and len(to_compute) > 1:
                    continue
                candidate = False
                if existing_terms_lines_index < len(existing_terms_lines):
                    # Update existing line.
                    candidate = existing_terms_lines[existing_terms_lines_index]
                    existing_terms_lines_index += 1
                    candidate.update({
                        'date_maturity': date_maturity,
                        'amount_currency': -amount_currency,
                        'debit': balance < 0.0 and -balance or 0.0,
                        'credit': balance > 0.0 and balance or 0.0,
                    })
                else:
                    # Create new line.
                    create_method = in_draft_mode and self.env['account.move.line'].new or self.env[
                        'account.move.line'].create
                    if balance:
                        candidate = create_method({
                            'name': self.payment_reference or '',
                            'debit': balance < 0.0 and -balance or 0.0,
                            'credit': balance > 0.0 and balance or 0.0,
                            'quantity': 1.0,
                            'amount_currency': -amount_currency,
                            'date_maturity': date_maturity,
                            'move_id': self.id,
                            'currency_id': self.currency_id.id,
                            'account_id': account.id,
                            'partner_id': self.commercial_partner_id.id,
                            'exclude_from_invoice_tab': True,
                        })
                if candidate:
                    new_terms_lines += candidate
                if in_draft_mode and candidate:
                    candidate.update(candidate._get_fields_onchange_balance())
            return new_terms_lines

        existing_terms_lines = self.line_ids.filtered(
            lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
        others_lines = self.line_ids.filtered(
            lambda line: line.account_id.user_type_id.type not in ('receivable', 'payable'))
        company_currency_id = self.company_id.currency_id
        total_balance = sum(others_lines.mapped(lambda l: company_currency_id.round(l.balance)))
        total_amount_currency = sum(others_lines.mapped('amount_currency'))

        if not others_lines:
            self.line_ids -= existing_terms_lines
            return

        computation_date = _get_payment_terms_computation_date(self)
        account = _get_payment_terms_account(self, existing_terms_lines)
        to_compute = _compute_payment_terms(self, computation_date, total_balance, total_amount_currency)
        new_terms_lines = _compute_diff_payment_terms_lines(self, existing_terms_lines, account, to_compute)

        # Remove old terms lines that are no longer needed.
        self.line_ids -= existing_terms_lines - new_terms_lines

        if new_terms_lines:
            self.payment_reference = new_terms_lines[-1].name or ''
            self.invoice_date_due = new_terms_lines[-1].date_maturity


    def _reconciled_move_line(self):
        for line in self.line_ids:
            id_move = []
            if line.reconciled_move_id:
                id_move.append(line.reconciled_move_id.id)
                id_move.append(line.id)
                domain = [('id', 'in', id_move)]
                move_lines = self.env['account.move.line'].search(domain)
                for line in move_lines:
                    line.reconciled = False
                move_lines.reconcile()

    def action_post(self):
        res = super(AccountMove, self).action_post()
        self._reconciled_move_line()
        return res

    def button_draft(self):
        res = super(AccountMove, self).button_draft()
        for line in self.line_ids:
            if line.ineco_vat:
                line.ineco_vat.write({'vatprd': False})
            vats = self.env['ineco.account.vat'].search([('move_id', '=', self.id)])
            for vat in vats:
                vat.write({'vatprd': False})
        if self.journal_id.input_tax:
            self.posted_before = False
            self.write({'auto_post': False, 'state': 'cancel'})
            self.unlink()
            view = self.env.ref("ineco_thai_account.view_ineco_purchase_vat_tree", False) or self.env['ir.ui.view']
            return {
                'name': "ภาษีหัก ณ ที่จ่าย()",
                'view_mode': 'tree',
                'views': [(view.id, "tree")],
                'res_model': 'ineco.account.vat',
                'type': 'ir.actions.act_window',
                'context': {'search_default_false_vat': True},
                'domain': [('tax_purchase_wait_ok', '=', True), ('move_line_id', '!=', False)],
            }
        return res

    def _post(self, soft=True):
        """Post/Validate the documents.

        Posting the documents will give it a number, and check that the document is
        complete (some fields might not be required if not posted but are required
        otherwise).
        If the journal is locked with a hash table, it will be impossible to change
        some fields afterwards.

        :param soft (bool): if True, future documents are not immediately posted,
            but are set to be auto posted automatically at the set accounting date.
            Nothing will be performed on those documents before the accounting date.
        :return Model<account.move>: the documents that have been posted
        """
        if not self.env.su and not self.env.user.has_group('account.group_account_invoice'):
            raise AccessError(_("You don't have the access rights to post an invoice."))

        for invoice in self.filtered(lambda move: move.is_invoice(include_receipts=True)):
            if invoice.quick_edit_mode and invoice.quick_edit_total_amount and invoice.quick_edit_total_amount != invoice.amount_total:
                raise UserError(_(
                    "The current total is %s but the expected total is %s. In order to post the invoice/bill, "
                    "you can adjust its lines or the expected Total (tax inc.).",
                    formatLang(self.env, invoice.amount_total, currency_obj=invoice.currency_id),
                    formatLang(self.env, invoice.quick_edit_total_amount, currency_obj=invoice.currency_id),
                ))
            if invoice.partner_bank_id and not invoice.partner_bank_id.active:
                raise UserError(_(
                    "The recipient bank account linked to this invoice is archived.\n"
                    "So you cannot confirm the invoice."
                ))
            if float_compare(invoice.amount_total, 0.0, precision_rounding=invoice.currency_id.rounding) < 0:
                raise UserError(_(
                    "You cannot validate an invoice with a negative total amount. "
                    "You should create a credit note instead. "
                    "Use the action menu to transform it into a credit note or refund."
                ))

            if not invoice.partner_id:
                if invoice.is_sale_document():
                    raise UserError(_("The field 'Customer' is required, please complete it to validate the Customer Invoice."))
                elif invoice.is_purchase_document():
                    raise UserError(_("The field 'Vendor' is required, please complete it to validate the Vendor Bill."))

            # Handle case when the invoice_date is not set. In that case, the invoice_date is set at today and then,
            # lines are recomputed accordingly.
            if not invoice.invoice_date:
                if invoice.is_sale_document(include_receipts=True):
                    invoice.invoice_date = fields.Date.context_today(self)
                elif invoice.is_purchase_document(include_receipts=True):
                    raise UserError(_("The Bill/Refund date is required to validate this document."))

        if soft:
            future_moves = self.filtered(lambda move: move.date > fields.Date.context_today(self))
            for move in future_moves:
                if move.auto_post == 'no':
                    move.auto_post = 'at_date'
                msg = _('This move will be posted at the accounting date: %(date)s', date=format_date(self.env, move.date))
                move.message_post(body=msg)
            to_post = self - future_moves
        else:
            to_post = self

        for move in to_post:
            if move.state == 'posted':
                raise UserError(_('The entry %s (id %s) is already posted.') % (move.name, move.id))
            if not move.line_ids.filtered(lambda line: line.display_type not in ('line_section', 'line_note')):
                raise UserError(_('You need to add a line before posting.'))
            if move.auto_post != 'no' and move.date > fields.Date.context_today(self):
                date_msg = move.date.strftime(get_lang(self.env).date_format)
                raise UserError(_("This move is configured to be auto-posted on %s", date_msg))
            if not move.journal_id.active:
                raise UserError(_(
                    "You cannot post an entry in an archived journal (%(journal)s)",
                    journal=move.journal_id.display_name,
                ))
            if move.display_inactive_currency_warning:
                raise UserError(_(
                    "You cannot validate a document with an inactive currency: %s",
                    move.currency_id.name
                ))

            affects_tax_report = move._affect_tax_report()
            lock_dates = move._get_violated_lock_dates(move.date, affects_tax_report)
            if lock_dates:
                move.date = move._get_accounting_date(move.invoice_date or move.date, affects_tax_report)

        # Create the analytic lines in batch is faster as it leads to less cache invalidation.
        to_post.line_ids._create_analytic_lines()
        to_post.write({
            'state': 'posted',
            'posted_before': True,
        })

        # Trigger copying for recurring invoices
        to_post.filtered(lambda m: m.auto_post not in ('no', 'at_date'))._copy_recurring_entries()

        for invoice in to_post:
            # Fix inconsistencies that may occure if the OCR has been editing the invoice at the same time of a user. We force the
            # partner on the lines to be the same as the one on the move, because that's the only one the user can see/edit.
            wrong_lines = invoice.is_invoice() and invoice.line_ids.filtered(lambda aml:
                aml.partner_id != invoice.commercial_partner_id
                and aml.display_type not in ('line_note', 'line_section')
            )
            if wrong_lines:
                wrong_lines.write({'partner_id': invoice.commercial_partner_id.id})

            invoice.message_subscribe([
                p.id
                for p in [invoice.partner_id]
                if p not in invoice.sudo().message_partner_ids
            ])

            # Compute 'ref' for 'out_invoice'.

            if invoice.move_type == 'out_invoice' and not invoice.payment_reference:
                to_write = {
                    'payment_reference': invoice._get_invoice_computed_reference(),
                    'line_ids': []
                }

                for line in invoice.line_ids.filtered(lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable')):
                    to_write['line_ids'].append((1, line.id, {'name': to_write['payment_reference']}))

                # Remove payment_reference and set internal_number for reuse name of invoice
                del(to_write['payment_reference'])
                to_write['internal_number'] = invoice.name
                #
                invoice.write(to_write)

            if (
                invoice.is_sale_document()
                and invoice.journal_id.sale_activity_type_id
                and (invoice.journal_id.sale_activity_user_id or invoice.invoice_user_id).id not in (self.env.ref('base.user_root').id, False)
            ):
                invoice.activity_schedule(
                    date_deadline=min((date for date in invoice.line_ids.mapped('date_maturity') if date), default=invoice.date),
                    activity_type_id=invoice.journal_id.sale_activity_type_id.id,
                    summary=invoice.journal_id.sale_activity_note,
                    user_id=invoice.journal_id.sale_activity_user_id.id or invoice.invoice_user_id.id,
                )

        customer_count, supplier_count = defaultdict(int), defaultdict(int)
        for invoice in to_post:
            if invoice.is_sale_document():
                customer_count[invoice.partner_id] += 1
            elif invoice.is_purchase_document():
                supplier_count[invoice.partner_id] += 1
        for partner, count in customer_count.items():
            (partner | partner.commercial_partner_id)._increase_rank('customer_rank', count)
        for partner, count in supplier_count.items():
            (partner | partner.commercial_partner_id)._increase_rank('supplier_rank', count)

        # Trigger action for paid invoices if amount is zero
        to_post.filtered(
            lambda m: m.is_invoice(include_receipts=True) and m.currency_id.is_zero(m.amount_total)
        )._invoice_paid_hook()

        return to_post

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    _order = "move_id, debit desc, credit desc"

    @api.depends('account_id')
    def _get_tax(self):
        for data in self:
            if data.account_id.tax_sale_ok and not data.account_id.tax_sale_wait:
                data.tax_ok = True
            elif data.account_id.tax_purchase_ok and not data.account_id.wait:
                data.tax_ok = True
            else:
                data.tax_ok = False

    @api.depends('account_id')
    def _get_cheque(self):
        for data in self:
            data.cheque_ok = data.account_id.cheque_in_ok or data.account_id.cheque_out_ok or False

    @api.depends('account_id')
    def _get_wht(self):
        for data in self:
            data.wht_ok = data.account_id.wht_sale_ok or data.account_id.wht_purchase_ok or False
            data.wht_sale_ok = data.account_id.wht_sale_ok or False
            data.wht_purchase_ok = data.account_id.wht_purchase_ok or False

    @api.depends('account_id')
    def _get_account_type(self):
        for data in self:
            data.receivable_ok = data.account_id.user_type_id.type == 'receivable' or False
            data.payable_ok = data.account_id.user_type_id.type == 'payable' or False

    # inherit

    @api.depends('move_id')
    def _compute_parent_state(self):
        self.parent_state = self.move_id.state

    ineco_vat = fields.Many2one('ineco.account.vat', string='ineco_vat', ondelete='cascade')
    ineco_iv = fields.Char(string=u'เลขที่ใบกำกับ', size=32, required=False, copy=False, tracking=True,
                           # default='New'
                           )
    vat_ids = fields.One2many('ineco.account.vat', 'move_line_id', string='Vat', )
    wht_ids = fields.One2many('ineco.wht', 'move_line_id', string='With Holding Tax', )
    cheque_ids = fields.One2many('ineco.cheque', 'move_line_id', string='Cheques', )
    tax_ok = fields.Boolean(string='Tax Ok', compute='_get_tax', readonly=True)
    wht_ok = fields.Boolean(string='WHT Ok', compute='_get_wht', readonly=True)
    wht_sale_ok = fields.Boolean(string='WHT Sale Ok', compute='_get_wht', readonly=True)
    wht_purchase_ok = fields.Boolean(string='WHT Purchase Ok', compute='_get_wht', readonly=True)
    receivable_ok = fields.Boolean(string='Receivable Ok', compute='_get_account_type', readonly=True)
    payable_ok = fields.Boolean(string='Payable Ok', compute='_get_account_type', readonly=True)
    cheque_ok = fields.Boolean(string='Cheque Ok', compute='_get_cheque', readonly=True)
    date_maturity = fields.Date(string='Due date', index=True, required=False,
                                help="This field is used for payable and receivable journal entries. You can put the limit date for the payment of this line.")
    foreign = fields.Boolean(u'ต่างประเทศ')
    foreign_receivable = fields.Float(u'รับต่างประเทศ')

    is_required_partner = fields.Boolean(string='Required Partner', compute='_compute_is_required_partner', store=True,
                                         readonly=False)
    reconciled_move_id = fields.Many2one('account.move.line', string=u'เลขที่เอกสาร reconciled', copy=False, index=True,
                                         )

    @api.onchange('reconciled_move_id')
    def _up_reconciled_move_id(self):
        for line in self:
            if line.reconciled_move_id.credit > 0:
                line.debit = abs(line.reconciled_move_id.amount_residual)
            if line.reconciled_move_id.debit > 0:
                line.credit = abs(line.reconciled_move_id.amount_residual)

    @api.depends('account_id', 'move_id.state')
    def _compute_is_required_partner(self):
        for line in self:
            # line.is_required_partner = line.account_id.user_type_id.type in ('receivable', 'payable')
            if line.account_id.is_partner:
                line.is_required_partner = True
            else:
                line.is_required_partner = False

    def _prepare_reconciliation_partials(self):
        # แก้ตัดเงินต่างประเทศ
        ''' Prepare the partials on the current journal items to perform the reconciliation.
        /!\ The order of records in self is important because the journal items will be reconciled using this order.

        :return: A recordset of account.partial.reconcile.
        '''
        debit_lines = iter(self.filtered('debit'))
        credit_lines = iter(self.filtered('credit'))
        debit_line = None
        credit_line = None

        debit_amount_residual = 0.0
        debit_amount_residual_currency = 0.0
        credit_amount_residual = 0.0
        credit_amount_residual_currency = 0.0
        debit_line_currency = None
        credit_line_currency = None

        partials_vals_list = []

        while True:
            # Move to the next available debit line.
            if not debit_line:
                debit_line = next(debit_lines, None)
                if not debit_line:
                    break
                debit_amount_residual = debit_line.amount_residual

                if debit_line.currency_id:
                    debit_amount_residual_currency = debit_line.amount_residual_currency
                    debit_line_currency = debit_line.currency_id
                else:
                    debit_amount_residual_currency = debit_amount_residual
                    debit_line_currency = debit_line.company_currency_id

            # Move to the next available credit line.
            if not credit_line:
                credit_line = next(credit_lines, None)
                if not credit_line:
                    break
                credit_amount_residual = credit_line.amount_residual

                if credit_line.currency_id:
                    credit_amount_residual_currency = credit_line.amount_residual_currency
                    credit_line_currency = credit_line.currency_id
                else:
                    credit_amount_residual_currency = credit_amount_residual
                    credit_line_currency = credit_line.company_currency_id

                if credit_line.foreign:  # รับเงินต่างประเทศ
                    credit_amount_residual_currency = -credit_line.foreign_receivable
                    credit_line_currency = credit_line.currency_id

            min_amount_residual = min(debit_amount_residual, -credit_amount_residual)
            if debit_line_currency == credit_line_currency:
                # Reconcile on the same currency.

                # The debit line is now fully reconciled.
                if debit_line_currency.is_zero(debit_amount_residual_currency) or debit_amount_residual_currency < 0.0:
                    debit_line = None
                    continue

                # The credit line is now fully reconciled.
                if credit_line_currency.is_zero(
                        credit_amount_residual_currency) or credit_amount_residual_currency > 0.0:
                    credit_line = None
                    continue

                min_amount_residual_currency = min(debit_amount_residual_currency, -credit_amount_residual_currency)
                min_debit_amount_residual_currency = min_amount_residual_currency
                min_credit_amount_residual_currency = min_amount_residual_currency


            else:
                # Reconcile on the company's currency.

                # The debit line is now fully reconciled.
                if debit_line.company_currency_id.is_zero(debit_amount_residual) or debit_amount_residual < 0.0:
                    debit_line = None
                    continue

                # The credit line is now fully reconciled.
                if credit_line.company_currency_id.is_zero(credit_amount_residual) or credit_amount_residual > 0.0:
                    credit_line = None
                    continue

                min_debit_amount_residual_currency = credit_line.company_currency_id._convert(
                    min_amount_residual,
                    debit_line.currency_id,
                    credit_line.company_id,
                    credit_line.date,
                )
                min_credit_amount_residual_currency = debit_line.company_currency_id._convert(
                    min_amount_residual,
                    credit_line.currency_id,
                    debit_line.company_id,
                    debit_line.date,
                )

            debit_amount_residual -= min_amount_residual
            debit_amount_residual_currency -= min_debit_amount_residual_currency
            credit_amount_residual += min_amount_residual
            credit_amount_residual_currency += min_credit_amount_residual_currency

            partials_vals_list.append({
                'amount': min_amount_residual,
                'debit_amount_currency': min_debit_amount_residual_currency,
                'credit_amount_currency': min_credit_amount_residual_currency,
                'debit_move_id': debit_line.id,
                'credit_move_id': credit_line.id,
            })
        return partials_vals_list

    def action_open_vat(self):
        self.ensure_one()
        view = self.env.ref("ineco_thai_account.view_new_ineco_account_vat_tree", False) or self.env['ir.ui.view']
        return {
            'name': "ภาษีมูลค่าเพิ่ม",
            'view_mode': 'tree',
            'views': [(view.id, "tree")],
            'res_model': 'ineco.account.vat',
            'type': 'ir.actions.act_window',
            'context': {'default_move_line_id': self.id},
            'domain': ['|', '|', ('move_line_id', '=', self.id), ('invoice_id', '=', self.move_id.id),
                       ('name', '=', self.ref)],
        }

    def action_open_wht_purchase(self):
        self.ensure_one()
        view = self.env.ref("ineco_thai_account.ineco_wht_tree", False) or self.env['ir.ui.view']
        return {
            'name': "ภาษีหัก ณ ที่จ่าย",
            'view_mode': 'tree',
            'views': [(view.id, "tree")],
            'res_model': 'ineco.wht',
            'type': 'ir.actions.act_window',
            'context': {'default_move_line_id': self.id},
            'domain': ['|', '|', '|', ('move_line_id', '=', self.id),
                       ('voucher_id', '=', self.move_id.id),
                       ('supplier_payment_id', '=', self.move_id.id),
                       ('supplier_deposit_id', '=', self.move_id.id)],
        }

    def action_open_wht_sale(self):
        self.ensure_one()
        view = self.env.ref("ineco_thai_account.ineco_wht_tree", False) or self.env['ir.ui.view']
        return {
            'name': "ภาษีถูกหัก ณ ที่จ่าย",
            'view_mode': 'tree',
            'views': [(view.id, "tree")],
            'res_model': 'ineco.wht',
            'type': 'ir.actions.act_window',
            'context': {'default_move_line_id': self.id},
            'domain': ['|', '|', '|', ('move_line_id', '=', self.id),
                       ('voucher_id', '=', self.move_id.id),
                       ('customer_payment_id', '=', self.move_id.id),
                       ('customer_deposit_id', '=', self.move_id.id)],
        }

    def action_open_cheque(self):
        self.ensure_one()
        view = self.env.ref("ineco_thai_account.view_ineco_cheque_tree", False) or self.env['ir.ui.view']
        return {
            'name': "เช็ค",
            'view_mode': 'tree',
            'views': [(view.id, "tree")],
            'res_model': 'ineco.cheque',
            'type': 'ir.actions.act_window',
            'context': {'default_move_line_id': self.id},
            'domain': ['|', ('move_line_id', '=', self.id), ('move_id', '=', self.move_id.id)],
        }
