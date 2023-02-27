# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools
from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta


class AccountMove(models.Model):
    _inherit = 'account.move'

    period_id = fields.Many2one('ineco.account.period', string='งวดบัญชี', compute='_compute_period', store=True,
                                readonly=True)

    @api.depends("date")
    def _compute_period(self):
        for move in self:
            periods = self.env['ineco.account.period'].finds(dt=move.date)
            if periods:
                if len(periods) > 1:
                    move.period_id = periods[0]
                else:
                    move.period_id = periods
            else:
                raise ValidationError(_('[POST] ยังไม่มีการระบุงวดบัญชีในระบบ'))

    def _post(self, soft=True):
        if not self.move_type in ['out_invoice', 'out_refund','in_invoice','in_refund']:
            if self.period_id:
                if self.period_id.state == 'draft':
                    return super(AccountMove, self)._post(soft=soft)
                else:
                    raise ValidationError(_('ไม่สามารถปรับเอกสารเป็น POST ได้ เนื่องจากมีการปิดงวดบัญชีไปแล้ว'))
            else:
                periods = self.env['ineco.account.period'].finds(dt=self.date)
                if periods:
                    if len(periods) > 1:
                        periods = periods[0]
                        self.period_id = periods
                    if periods.state == 'draft':
                        return super(AccountMove, self)._post(soft=soft)
                    else:
                        raise ValidationError(_('ไม่สามารถปรับเอกสารเป็น POST ได้ เนื่องจากมีการปิดงวดบัญชีไปแล้ว'))
                else:
                    raise ValidationError(_('[POST] ยังไม่มีการระบุงวดบัญชีในระบบ'))
        else:
            periods = self.env['ineco.account.period'].finds(dt=self.invoice_date)
            if periods:
                if len(periods) > 1:
                    periods = periods[0]
                    self.period_id = periods
                if periods.state == 'draft':
                    return super(AccountMove, self)._post(soft=soft)
                else:
                    raise ValidationError(_('ไม่สามารถปรับเอกสารเป็น POST ได้ เนื่องจากมีการปิดงวดบัญชีไปแล้ว'))
            else:
                raise ValidationError(_('[POST] ยังไม่มีการระบุงวดบัญชีในระบบ'))


    def button_draft(self):
        if self.period_id:
            if self.period_id.state == 'draft':
                return super(AccountMove, self).button_draft()
            else:
                raise ValidationError(_('ไม่สามารถปรับเอกสารเป็นดราฟได้ เนื่องจากมีการปิดงวดบัญชีไปแล้ว'))
        else:
            periods = self.env['ineco.account.period'].finds(dt=self.invoice_date)
            if not periods:
                raise ValidationError(_('[DRAFT] ยังไม่มีการระบุงวดบัญชีในระบบ'))
            else:
                self.period_id = periods.id
                return super(AccountMove, self).button_draft()

    def button_cancel(self):
        if self.period_id:
            if self.period_id.state == 'draft':
                return super(AccountMove, self).button_cancel()
            else:
                raise ValidationError(_('ไม่สามารถปรับเอกสารเป็น CANCEL ได้ เนื่องจากมีการปิดงวดบัญชีไปแล้ว'))
        else:
            periods = self.env['ineco.account.period'].finds(dt=self.invoice_date)
            if not periods:
                raise ValidationError(_('[CANCEL] ยังไม่มีการระบุงวดบัญชีในระบบ'))
            else:
                self.period_id = periods.id
                return super(AccountMove, self).button_cancel()

