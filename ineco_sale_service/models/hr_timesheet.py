# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from lxml import etree
import re

from odoo import api, Command, fields, models, _, _lt
from odoo.exceptions import UserError, AccessError, ValidationError
from odoo.osv import expression

class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    expense_id = fields.Many2one('hr.expense', string='Expense', readonly=True, copy=False)
    is_select = fields.Boolean(string='Select', default=False)
    state_expense = fields.Selection(related='expense_id.state', string='Expense State', readonly=True, store=True)


