# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools
from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta


class AccountFiscalYear(models.Model):
    _name = 'ineco.account.fiscalyear'
    _description = 'Account Fiscal Year'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "date_start"

    name = fields.Char(string='ปีภาษี(พ.ศ.)', required=True)
    code = fields.Char(string='รหัส', required=True)
    # company_id = fields.Many2one('res.company', string='บริษัท', required=True)
    company_id = fields.Many2one('res.company', string='บริษัท', store=True, readonly=True, change_default=True,
                                 default=lambda self: self.env.company)
    date_start = fields.Date(string='วันที่เริ่มต้น', required=True)
    date_finish = fields.Date(string='วันที่สิ้นสุด', required=True)
    period_ids = fields.One2many('ineco.account.period', 'fiscalyear_id', string='งวดบัญชี')
    state = fields.Selection([('draft', 'Open'), ('done', 'Closed')], string='สถานะ', default='draft', copy=False)

    @api.constrains('date_finish', 'date_start')
    def _check_duration(self):
        self.ensure_one()
        if self.date_finish < self.date_start:
            raise ValidationError(_('The start date of a fiscal year must precede its end date.'))

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('code', '=ilike', name.split(' ')[0] + '%'), ('name', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&', '!'] + domain[1:]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)

    def create_period(self, interval=1):
        self.ensure_one()
        period_obj = self.env['ineco.account.period']
        ds = self.date_start
        open_period = period_obj.create({
            'name': "%s %s" % (_('Opening Period'), ds.strftime('%Y')),
            'code': ds.strftime('00/%Y'),
            'date_start': ds,
            'date_finish': ds,
            'is_opened': True,
            'company_id': self.company_id.id,
            'fiscalyear_id': self.id
        })
        close_period = period_obj.create({
            'name': "%s %s" % (_('Closing Period'), self.date_finish.strftime('%Y')),
            'code': self.date_finish.strftime('99/%Y'),
            'date_start': self.date_finish,
            'date_finish': self.date_finish,
            'is_closed': True,
            'company_id': self.company_id.id,
            'fiscalyear_id': self.id
        })
        while ds < self.date_finish:
            de = ds + relativedelta(months=interval, days=-1)

            if de > self.date_finish:
                de = self.date_finish

            current_period = period_obj.create({
                'name': ds.strftime('%m/%Y'),
                'code': ds.strftime('%m/%Y'),
                'date_start': ds.strftime('%Y-%m-%d'),
                'date_finish': de.strftime('%Y-%m-%d'),
                'company_id': self.company_id.id,
                'fiscalyear_id': self.id,
            })
            ds = ds + relativedelta(months=interval)

    def create_period3(self):
        return self.create_period(interval=3)
