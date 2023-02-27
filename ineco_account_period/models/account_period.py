# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools
from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError


class AccountPeriod(models.Model):
    _name = 'ineco.account.period'
    _description = 'Account Period'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    # _order = 'date_start, id'

    name = fields.Char(string='ชื่องวดบัญชี', required=True)
    code = fields.Char(string='รหัสงวด', required=True)
    is_opened = fields.Boolean(string='งวดยอดยกมาก', copy=False)
    is_closed = fields.Boolean(string='งวดปิดบัญชี', copy=False)
    date_start = fields.Date(string='วันที่เริ่มต้น', required=True)
    date_finish = fields.Date(string='วันที่สิ้นสุด', required=True)
    state = fields.Selection([('draft', 'Open'), ('done', 'Closed')], string='สถานะ', default='draft', copy=False)
    # company_id = fields.Many2one('res.company', string='บริษัท', required=True)
    company_id = fields.Many2one('res.company', string='บริษัท', store=True, readonly=True, change_default=True,
                                 default=lambda self: self.env.company)
    fiscalyear_id = fields.Many2one('ineco.account.fiscalyear', string='ปีภาษี', required=True, ondelete='cascade')
    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id)', 'The name of the period must be unique per company!'),
    ]

    @api.constrains('date_finish', 'date_start')
    def _check_duration(self):
        self.ensure_one()
        if self.date_finish < self.date_start:
            raise ValidationError(_('The duration of the Period(s) is/are invalid.'))

    @api.returns('self')
    def next(self, period, step):
        ids = self.search([('date_start', '>', period.date_start)])
        if len(ids) >= step:
            return ids[step - 1]
        return False

    @api.returns('self')
    def finds(self, dt=None):
        company_id = self.env.company.id
        if not dt:
            dt = fields.date.today()
        args = [('date_start', '<=', dt),
                ('date_finish', '>=',dt),
                ('is_opened','=',False),
                ('is_closed','=',False),
                ('company_id', '=', company_id)
                ]
        result = self.search(args)
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('code', '=ilike', name.split(' ')[0] + '%'), ('name', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&', '!'] + domain[1:]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)

    def _do_process_before_close_period(self):
        """
        มีกระบวนการอะไรทำก่อนปิดบัญชีให้มาใส่ตรงนี้
        """
        self.ensure_one()
        return True

    def _do_process_before_draft_period(self):
        """
        มีกระบวนการอะไรที่จะเปลี่ยนจาก Open->Draft ให้มาใส่ตรงนี้
        """
        self.ensure_one()
        return True

    def button_draft(self):
        for data in self:
            data._do_process_before_draft_period()
            data.state = 'draft'

    def button_done(self):
        for data in self:
            data._do_process_before_close_period()
            data.state = 'done'
