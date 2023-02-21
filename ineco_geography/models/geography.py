# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.osv import expression


# from openerp import api, fields, models, _


class InecoGeography(models.Model):
    _name = "ineco.geography"
    _description = "Geography"
    _order = 'code, name'

    name = fields.Char(string='Name', required=True, copy=False, index=True, tracking=True)
    code = fields.Char(string='Code', required=True, copy=False, index=True, tracking=True)

    active = fields.Boolean('Active', default=True)


class InecoProvince(models.Model):
    _name = "ineco.province"
    _description = "Province"
    _order = 'code, name'

    name = fields.Char(string='Name', required=True, copy=False, index=True, tracking=True)
    code = fields.Char(string='Code', required=True, copy=False, index=True, tracking=True)
    geo_id = fields.Many2one('ineco.geography', string='Geography', required=True, copy=False, index=True,
                             tracking=True)

    active = fields.Boolean('Active', default=True)

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('code', '=ilike', name.split(' ')[0] + '%'), ('name', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&', '!'] + domain[1:]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)


class InecoAmphur(models.Model):
    _name = "ineco.amphur"
    _description = "Amphur"
    _order = 'code, name'

    name = fields.Char(string='Name', required=True, copy=False, index=True, tracking=True)
    code = fields.Char(string='Code', required=True, copy=False, index=True, tracking=True)
    geo_id = fields.Many2one('ineco.geography', string='Geography', required=True, copy=False, index=True,
                             tracking=True)
    province_id = fields.Many2one('ineco.province', string='Province', copy=False, index=True,
                                  tracking=True)

    active = fields.Boolean('Active', default=True)

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('code', '=ilike', name.split(' ')[0] + '%'), ('name', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&', '!'] + domain[1:]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)


class InecoDistrict(models.Model):
    _name = "ineco.district"
    _description = "District"
    _order = 'code, name'

    name = fields.Char(string='Name', required=True, copy=False, index=True, tracking=True)
    code = fields.Char(string='Code', required=True, copy=False, index=True, tracking=True)
    geo_id = fields.Many2one('ineco.geography', string='Geography', required=True, copy=False, index=True,
                             tracking=True)
    province_id = fields.Many2one('ineco.province', string='Province', copy=False, index=True,
                                  tracking=True)
    amphur_id = fields.Many2one('ineco.amphur', string='Amphur', copy=False, index=True, tracking=True)

    active = fields.Boolean('Active', default=True)

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('code', '=ilike', name.split(' ')[0] + '%'), ('name', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&', '!'] + domain[1:]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)

    @api.depends('name', 'code', 'geo_id', 'province_id', 'amphur_id')
    def name_get(self):
        res = []
        for record in self:
            name = record.name
            if self._context.get('show_fully', False):
                name = record.name + ' / ' + record.amphur_id.name + ' / ' + record.province_id.name
            res.append((record.id, name))
        return res


class InecoZipcode(models.Model):
    _name = "ineco.zipcode"
    _description = "Zipcode"
    _order = 'name'

    name = fields.Char(string='Name', required=True, copy=False, index=True, tracking=True)
    province_id = fields.Many2one('ineco.province', string='Province', required=True, copy=False, index=True,
                                  tracking=True)
    amphur_id = fields.Many2one('ineco.amphur', string='Amphur', copy=False, index=True, tracking=True)
    district_id = fields.Many2one('ineco.district', string='District', copy=False, index=True,
                                  tracking=True)

    active = fields.Boolean('Active', default=True)
