# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
import bahttext
import unicodecsv as csv
from io import BytesIO
import base64


class InecoWhtType(models.Model):
    _name = 'ineco.wht.type'
    _description = 'ประเภท WHT'

    name = fields.Char(string='Description', required=True)
    printed = fields.Char(string='To Print')
    sequence = fields.Integer(string='Sequence')

    _sql_constraints = [
        ('ineco_wht_unique', 'unique (sequence)', 'Sequence must be unique!')
    ]


class InecoWhtLine(models.Model):
    _name = 'ineco.wht.line'
    _description = 'With Holding Tax Line'
    _inherit = ['mail.thread']

    @api.depends('percent', 'base_amount')
    def _compute_tax(self):
        if self.percent and self.base_amount:
            self.tax = (self.percent / 100) * self.base_amount

    name = fields.Char(string='คำอธิบาย', tracking=True)
    wht_type_id = fields.Many2one('ineco.wht.type', string='ประเภท', required=True, tracking=True)
    date_doc = fields.Date(string='วันที่', required=True, default=fields.Datetime.now(), tracking=True)
    percent = fields.Float(string='เปอร์เซ็นต์', digits=(12, 2), default=3.0, tracking=True)
    wht_id = fields.Many2one('ineco.wht', string='With Holding Tax', copy=False, tracking=True)
    note = fields.Text(string='หมายเหตุ', tracking=True)
    base_amount = fields.Float(string='ฐานภาษี', digits=(12, 2), copy=False, tracking=True)
    tax = fields.Float(string='ภาษี', digits=(12, 2), compute='_compute_tax', store=True)


class InecoWhtPnd(models.Model):
    _name = 'ineco.wht.pnd'
    _description = "WHT PND"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.depends('wht_id')
    def _attachment_count(self):
        self.attach_count = len(self.wht_id)
        self.attach_no = len(self.wht_id) / 6 + 1
        val = val1 = 0.0
        for line in self.wht_id:
            val1 += line.base_amount
            val += line.tax
        self.total_tax = val
        self.total_amount = val1
        self.total_tax_send = val + self.add_amount or 0.0

    name = fields.Char(string='Description', tracking=False)
    account_fiscal_year = fields.Many2one('ineco.account.fiscalyear', string=u'ปี')
    account_period = fields.Many2one('ineco.account.period', string=u'เดือน',
                                     domain="[('fiscalyear_id','=',account_fiscal_year)]")
    date_pnd = fields.Date(string='Date', required=True, tracking=False)
    type_normal = fields.Boolean(string='Type Normal', tracking=False)
    type_special = fields.Boolean(string='Type Special', tracking=False)
    type_no = fields.Boolean(string='Type No', tracking=False)
    section_3 = fields.Boolean(string='Section 3', tracking=False)
    section_48 = fields.Boolean(string='Section 48', tracking=False)
    section_50 = fields.Boolean(string='Section 50', tracking=False)
    section_65 = fields.Boolean(string='Section 65', tracking=False)
    section_69 = fields.Boolean(string='Section 69', tracking=False)
    attach_pnd = fields.Boolean(string='Attach PND', tracking=False)
    wht_ids = fields.Many2many('ineco.wht', 'ineco_wht_pnds', 'pnd_id', 'wht_id', 'With holding taxes')

    wht_id = fields.One2many('ineco.wht', 'pnd_id', 'With holding tax')

    attach_count = fields.Integer(string='Attach Count', compute='_attachment_count')
    attach_no = fields.Integer(string='Attach No', compute='_attachment_count')
    total_amount = fields.Float(string='Total Amount', digits=(12, 2), compute='_attachment_count')
    total_tax = fields.Float(string='Total Tax', digits=(12, 2), compute='_attachment_count')
    total_tax_send = fields.Float(string='Tax Send', digits=(12, 2), compute='_attachment_count')
    add_amount = fields.Float(string='Add Amount', digits=(12, 2), default=0.0, tracking=False)
    note = fields.Text(string='Note', tracking=False)
    # company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id)
    company_id = fields.Many2one('res.company', string='Company', store=True, readonly=True, change_default=True,
                                 default=lambda self: self.env.company)

    pnd_type = fields.Selection([('pp4', '(4) PP3'), ('pp7', '(7) PP53')], 'PND Type', required=True,
                                index=True, tracking=False)
    file_save = fields.Binary('Save File', readonly=True)
    file_name = fields.Char('File Name')

    state = fields.Selection([('draft', 'Draft'), ('post', 'Posted'), ('cancel', 'Cancel')],
                             string=u'State', default='draft')

    wht_filing = fields.Selection([('normal', 'ยื่นปกติ'),
                                   ('add', 'ยื่นเพิ่มเติม'),
                                   ], string='ประเภทการยื่น', default='normal', required=True,tracking=True)

    def button_draft(self):
        self.ensure_one()
        # self.wht_id = False
        self.state = 'draft'
        return True

    def button_cancel(self):
        self.ensure_one()
        self.wht_id = False
        self.state = 'cancel'
        return True

    def export_pnd3(self):
        for data in self:
            self.get_pnd3()
            sql = """
            select * from (
                select
                    ''::varchar as space,
                    lpad(
                    ROW_NUMBER () OVER (ORDER BY iw.date_doc)::text,5,'0')::varchar as sequence,
                    rp.vat,
                    case when rp.branch_no is null then '00000'::varchar
                    else rp.branch_no::varchar end as title_code,
                    ''::varchar as title_name,
                    rp.name,
                    ''::varchar as lastname,
                    rp.street as address ,
                    id.name as th_tambon,
                    ia.name as th_amphur,
                    ip.name as th_province,
                    rp.zip,
                    (lpad (
                          extract(day from iw.date_doc)::text,2,'0' )
                    || '/' ||
                    lpad (
                     extract(month from iw.date_doc)::text,2,'0' )
                    || '/' ||
                     extract(year from iw.date_doc) + 543)::varchar  as date_doc,
                    (iwt.name || ' ' || iwl.note)::varchar(200) as description,
                    ltrim(to_char(iwl.percent, '00.00'))::varchar as percent,
                    ltrim(to_char(iwl.base_amount::numeric,'00000000000.00' ))::varchar as amount_untaxed,
                    ltrim(to_char(round(iwl.percent / 100 * iwl.base_amount, 2)::numeric,'0000000000.00'))::varchar as amount_tax,
                    iw.wht_filing,
                    '1'::varchar as always
                    from ineco_wht iw
                    left join ineco_wht_line iwl on iw.id = iwl.wht_id

                    left join res_company rc on iw.company_id = rc.id
                    left join res_partner rp2 on rc.partner_id = rp2.id

                    left join res_partner rp on iw.partner_id = rp.id
                    left join ineco_wht_type iwt on iwt.id = iwl.wht_type_id
                    
                    left join ineco_district id on id.id = rp.district_id
                    left join ineco_amphur ia on ia.id = rp.amphur_id
                    left join ineco_province ip on ip.id = rp.province_id

                    where wht_type = 'purchase'
			        and iw.date_doc BETWEEN (select date_start from ineco_account_period where id = %s) and (select date_finish from ineco_account_period where id = %s) 
                    and iw.wht_kind = '%s') as data1
                    where data1.wht_filing ='%s'
                    """
            self._cr.execute(sql % (data.account_period.id, data.account_period.id, 'pp4',data.wht_filing))
            buf = BytesIO()
            # with open('pnd.csv', 'wb') as outfile:
            wt = csv.writer(buf, delimiter='|', quoting=csv.QUOTE_MINIMAL, encoding='UTF-8')  # 'cp874F'

            for record in self._cr.fetchall():
                mydict = []
                for v in record:
                    mydict.append(v)
                wt.writerow(mydict)

            data.write({'file_save': base64.b64encode(buf.getvalue()),
                        'file_name': 'pnd3_' + data.account_period.name.replace('/', '-') + '.txt'  # '.csv'
                        })
            self.state = 'post'

        return True

    def export_pnd53(self):
        for data in self:
            self.get_pnd53()
            sql = """
            select * from (
                    select
                    --''::varchar as space,
                    lpad(
                    ROW_NUMBER () OVER (ORDER BY iw.date_doc)::text,1,'0')::varchar as sequence, 
                    rp.vat,
                    case when rp.branch_no is null then '00000'::varchar
                    else rp.branch_no::varchar end as title_code,
                    ''::varchar as titlename,
                    rp.name,
                    rp.street as address ,
                    id.name as th_tambon,
                    ia.name as th_amphur,
                    ip.name as th_province,
                    rp.zip,
                
                
                    (lpad (
                      extract(day from iw.date_doc)::text,2,'0' )
                    || '/' ||
                    lpad (
                     extract(month from iw.date_doc)::text,2,'0' )
                    || '/' ||
                     extract(year from iw.date_doc) + 543)::varchar  as date_doc,
                    (iwt.name || ' ' || iwl.note)::varchar(200) as description,
                    iwl.percent as percent,
                    iwl.base_amount::numeric as amount_untaxed,
                    (round(iwl.percent / 100 * iwl.base_amount, 2)) as amount_tax,
                    iw.wht_filing,
                    '1'::varchar as always
                    from ineco_wht iw
                    left join ineco_wht_line iwl on iw.id = iwl.wht_id
                
                    left join res_company rc on iw.company_id = rc.id
                    left join res_partner rp2 on rc.partner_id = rp2.id
                
                    left join res_partner rp on iw.partner_id = rp.id
                    left join ineco_wht_type iwt on iwt.id = iwl.wht_type_id
                
                    left join ineco_district id on id.id = rp.district_id
                    left join ineco_amphur ia on ia.id = rp.amphur_id
                    left join ineco_province ip on ip.id = rp.province_id
                   
                    where
                      wht_type = 'purchase'                      
                      and iw.date_doc BETWEEN (select date_start from ineco_account_period where id = %s) and (select date_finish from ineco_account_period where id = %s) 
                      and iw.wht_kind = '%s' ) as data1
                      where data1.wht_filing = '%s'
                          
                     """
            self._cr.execute(sql % (data.account_period.id, data.account_period.id, 'pp7',data.wht_filing))  # pp7
            buf = BytesIO()
            # with open('pnd.csv', 'wb') as outfile:
            wt = csv.writer(buf, delimiter='|', quoting=csv.QUOTE_MINIMAL, encoding='UTF-8')  # 'cp874F'
            for record in self._cr.fetchall():
                mydict = []
                for v in record:
                    mydict.append(v)
                wt.writerow(mydict)

            data.write({'file_save': base64.b64encode(buf.getvalue()),
                        'file_name': 'pnd53_' + data.account_period.name.replace('/', '-') + '.txt'  # '.csv'
                        })
            self.state = 'post'

        return True


    def get_pnd3(self):
        tax = self.env['ineco.wht'].search([
            ('date_doc', '>=', self.account_period.date_start),
            ('date_doc', '<=', self.account_period.date_finish),
            ('wht_type', '=', 'purchase'),
            ('wht_kind', '=', 'pp4'),
            ('pnd_id','=',False),
            ('wht_filing', '=', self.wht_filing)
        ])
        for pnd3 in tax:
            pnd3.pnd_id = self.id

    def get_pnd53(self):
        tax = self.env['ineco.wht'].search([
            ('date_doc', '>=', self.account_period.date_start),
            ('date_doc', '<=', self.account_period.date_finish),
            ('wht_type', '=', 'purchase'),
            ('wht_kind', '=', 'pp7'),
            ('pnd_id','=',False),
            ('wht_filing','=',self.wht_filing)
        ])
        for pnd53 in tax:
            pnd53.pnd_id = self.id


class InecoWht(models.Model):
    _name = 'ineco.wht'
    _description = 'With Holding Tax'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.depends('company_id')
    def _get_company_vat(self):
        for data in self:
            if data.company_id:
                data.company_full_address = (data.company_id.partner_id.street or '') + ' ' + \
                                            (data.company_id.partner_id.street2 or '') + ' ' + \
                                            (data.company_id.partner_id.city or '')

    @api.depends('partner_id')
    def _get_supplier_vat(self):
        for data in self:
            data.partner_full_address = (data.partner_id.street or '') + ' ' + \
                                        (data.partner_id.street2 or '') + ' ' + \
                                        (data.partner_id.city or '')

    @api.depends()
    def _get_moveline(self):
        for data in self:
            sql = 'select id from account_move_line where wht_id = %s' % (data.id)
            self._cr.execute(sql)
            res = self._cr.fetchone()
            data.move_line_id = res and res[0] or False

    @api.depends('line_ids')
    def _get_line_value(self):
        number5 = self.env['ineco.wht.type'].sudo().search([('sequence', '=', '500')])
        number6 = self.env['ineco.wht.type'].sudo().search([('sequence', '=', '600')])
        for data in self:
            for line in data.line_ids:
                if number5 and line.wht_type_id.id == number5.id:
                    data.has_number_5 = True
                    data.number5_base_amount = line.base_amount
                    data.number5_tax = line.tax
                elif number6 and line.wht_type_id.id == number6.id:
                    data.has_number_6 = True
                    data.number6_base_amount = line.base_amount
                    data.number6_tax = line.tax
                    data.number6_note = line.note

    name = fields.Char(string='เลขที่', required=True, default='/', tracking=True)
    date_doc = fields.Date(string='ลงวันที่', required=True, tracking=True)
    # company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id)
    company_id = fields.Many2one('res.company', string='Company', store=True, readonly=True, change_default=True,
                                 default=lambda self: self.env.company)
    company_vat_no = fields.Char(string='Company Vat No', related='company_id.vat', readonly=True,
                                 tracking=True)

    company_full_address = fields.Char(string='Company Address',
                                       store=True, readonly=True, compute='_get_company_vat',
                                       tracking=True)
    partner_id = fields.Many2one('res.partner', string='พาร์ทเนอร์', required=True, tracking=True)
    partner_vat_no = fields.Char(string='Vat No', related='partner_id.vat', readonly=True, tracking=True)
    partner_full_address = fields.Char(string='Partner',
                                       store=True, readonly=True, compute='_get_supplier_vat',
                                       tracking=True)
    account_id = fields.Many2one('account.account', string='Account', tracking=True)
    sequence = fields.Integer(string='Sequence', default=100)
    wht_type = fields.Selection([('sale', 'Sale'), ('purchase', 'Purchase')], string='ประเภท')
    wht_kind = fields.Selection([('pp1', '(1) PP1'),
                                 ('pp2', '(2) PP1'),
                                 ('pp3', '(3) PP2'),
                                 ('pp4', '(4) PP3'),
                                 ('pp5', '(5) PP2'),
                                 ('pp6', '(6) PP2'),
                                 ('pp7', '(7) PP53'),
                                 ], string='ภงด.', default='pp7', tracking=True)
    wht_payment = fields.Selection([('pm1', '(1) With holding tax'),
                                    ('pm2', '(2) Forever'),
                                    ('pm3', '(3) Once'),
                                    ('pm4', '(4) Other'),
                                    ], string='การชำระ', default='pm1', tracking=True)
    wht_filing = fields.Selection([('normal', 'ยื่นปกติ'),
                                    ('add', 'ยื่นเพิ่มเติม'),
                                    ], string='ประเภทการยื่น', default='normal', tracking=True)
    note = fields.Text(string='หมายเหตุ', tracking=True)
    line_ids = fields.One2many('ineco.wht.line', 'wht_id', string='WHT Lines', tracking=True)
    base_amount = fields.Float(string='ยอดเงิน', digits=(12, 2), compute='_compute_amount', store=True,
                               tracking=True, compute_sudo=True)
    tax = fields.Float(string='ภาษี', digits=(12, 2), compute='_compute_amount', store=True,
                       tracking=True, compute_sudo=True)
    tax_text = fields.Char(string='Baht Tax', compute='_compute_amount', tracking=True, compute_sudo=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('cancel', 'Cancelled'),
        ('done', 'Done'),
    ], 'Status', readonly=True, tracking=True)
    voucher_id = fields.Many2one('account.move', string='Voucher', tracking=True)
    has_number_5 = fields.Boolean(string='Is No 5', compute='_get_line_value', store=True)
    number5_base_amount = fields.Float(string='Base Amount (5)', compute='_get_line_value', digits=(12, 2), store=True)
    number5_tax = fields.Float(string='Tax (5)', compute='_get_line_value', digits=(12, 2), store=True)
    has_number_6 = fields.Boolean(string='Is No 6', compute='_get_line_value', store=True)
    number6_base_amount = fields.Float(string='Base Amount (6)', compute='_get_line_value', digits=(12, 2), store=True)
    number6_tax = fields.Float(string='Tax (6)', compute='_get_line_value', digits=(12, 2), store=True)
    number6_note = fields.Char(string='Note', compute='_get_line_value', store=True)
    move_line_id = fields.Many2one('account.move.line', string='Move Line', ondelete="restrict",
                                   tracking=True)
    customer_payment_id = fields.Many2one('ineco.customer.payment', string='Customer Payment', ondelete="restrict",
                                          tracking=True)
    customer_deposit_id = fields.Many2one('ineco.customer.deposit', string='Customer Deposit', ondelete="restrict",
                                          tracking=True)
    supplier_payment_id = fields.Many2one('ineco.supplier.payment', string='Supplier Payment', ondelete="restrict",
                                          tracking=True)
    supplier_deposit_id = fields.Many2one('ineco.supplier.deposit', string='Supplier Deposit', ondelete="restrict",
                                          tracking=True)

    cash_invoic_id = fields.Many2one('ineco.petty.cash.invoice', string='petty cash invoice', ondelete="restrict",
                                          tracking=True)

    pnd_id = fields.Many2one('ineco.wht.pnd', string=u'แบบยื่นภาษีหัก ณ ที่จ่าย', copy=False,
                             tracking=True)
    sp_amount = fields.Float(u'ฐานหัก', tracking=True)

    @api.depends('line_ids.base_amount', 'line_ids.tax')
    def _compute_amount(self):
        for data in self:
            val = val1 = 0.0
            for line in data.line_ids:
                val1 += line.base_amount
                val += line.tax
            data.tax = val
            data.base_amount = val1
            data.tax_text = '- ' + bahttext.bahttext(val) + ' -'

    def button_cancel(self):
        self.ensure_one()
        self.state = 'cancel'
        return True
