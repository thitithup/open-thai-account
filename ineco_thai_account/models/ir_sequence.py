# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class IrSequence(models.Model):
    _inherit = "ir.sequence"

    ineco_fiscalyear_id = fields.Many2one('ineco.account.fiscalyear', string=u'ปีบัญชี', required=False)



    def button_generate_sequence(self):
        for data in self:
            if data.ineco_fiscalyear_id:
                for period in data.ineco_fiscalyear_id.period_ids:
                    prd = self.env['ir.sequence.date_range']
                    periods = prd.search(
                        [('sequence_id', '=', data.id), ('date_from', '=', period.date_start),
                         ('date_to', '=', period.date_finish)], limit=1)
                    if not periods:
                        new_data = {
                            'date_from': period.date_start,
                            'date_to': period.date_finish,
                            'sequence_id': data.id,
                            'number_next': 1
                        }
                        prd.create(new_data)
