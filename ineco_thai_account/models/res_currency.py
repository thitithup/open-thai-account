# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import math
import re
import time
import traceback

from odoo import api, fields, models, tools, _

_logger = logging.getLogger(__name__)



class Currency(models.Model):
    _inherit = "res.currency"
    _description = "Currency"


    @api.model
    def _get_conversion_rate(self, from_currency, to_currency, company, date):
        currency_rates = (from_currency + to_currency)._get_rates(company, date)
        res = currency_rates.get(to_currency.id) * currency_rates.get(from_currency.id)
        return res

