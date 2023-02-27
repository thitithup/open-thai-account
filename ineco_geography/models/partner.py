# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    district_id = fields.Many2one('ineco.district', string='ตำบล/แขวง', index=True, ondelete='restrict')
    amphur_id = fields.Many2one('ineco.amphur', string='อำเภอ/เขต', index=True, ondelete='restrict')
    province_id = fields.Many2one('ineco.province', string='จังหวัด', index=True, ondelete='restrict')
    is_update_adr = fields.Boolean(string='ปรับที่อยู่แล้ว')
    show_thai_address = fields.Boolean(string='แสดงที่อยู่ไทย', default=True)

    @api.model
    def daily_update_partner_update_adr(self, id=False):
        pass
        # domin = [('is_update_adr', '=', False)]
        # if id:
        #     domin = [('id','=',id)]
        # partners = self.env['res.partner'].search(domin, limit=200)
        # # limit = 500
        # for partner in partners:
        #     partner.onchange_district_id()
        #     partner.is_update_adr = True

    @api.onchange('district_id')
    def onchange_district_id(self):
        if self.district_id:
            self.amphur_id = self.district_id.amphur_id.id
            self.province_id = self.district_id.province_id.id
            self.street2 = self.district_id.name + ' ' + self.district_id.amphur_id.name
            self.city = self.district_id.province_id.name
            zip = self.env['ineco.zipcode'].search([('district_id', '=', self.district_id.id),
                                                    ('amphur_id', '=', self.district_id.amphur_id.id),
                                                    ('province_id', '=', self.district_id.province_id.id)])
            if zip:
                self.zip = zip.name
