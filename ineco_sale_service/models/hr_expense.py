# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    project_task_id = fields.Many2one('project.task', string='Project Task',
                                      readonly=True,)

class Expense(models.Model):
    _inherit = "hr.expense"

    timesheet_id = fields.Many2one('account.analytic.line', string='Timesheet',)

    account_analytic_id = fields.Many2one('account.analytic.account', string='Analytic Account',)




