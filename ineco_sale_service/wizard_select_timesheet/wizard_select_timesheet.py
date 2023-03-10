# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-Today INECO LTD,. PART. (<http://www.ineco.co.th>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.addons.base.models.decimal_precision import dp


class WizardSelectTimesheet(models.TransientModel):
    _name = "wizard.select.timesheet"

    item_ids = fields.One2many('wizard.select.timesheet.line', 'order_id', string='Move Lines')

    @api.model
    def default_get(self, fields):
        res = super(WizardSelectTimesheet, self).default_get(fields)
        res_ids = self._context.get('active_ids')
        timesheet_obj = self.env['project.task']
        timeshees = timesheet_obj.browse(res_ids)
        items = []

        for line in timeshees.timesheet_ids:
            if line.is_select and not line.expense_id:
                line_data = {
                    'date': line.date,
                    'name': line.name,
                    'user_id': line.user_id.id,
                    'unit_amount': line.unit_amount,
                    'timesheet_id': line.id,
                }
                items.append([0, 0, line_data])
        res['item_ids'] = items
        return res

    def select_set_timesheet(self):
        res_ids = self._context.get('active_ids')
        timesheet_obj = self.env['project.task']
        timeshees = timesheet_obj.browse(res_ids)
        sheetsids = []

        for line in self.item_ids:
            data = {
                'date': line.date,
                'name': line.name,
                'payment_mode': 'own_account',
                'employee_id': line.user_id.employee_id.id,
                'total_amount': line.unit_amount * line.user_id.employee_id.hourly_cost,

                'product_id': line.product_id.id,
                'product_uom_id': line.product_id.uom_id.id,
                'account_analytic_id': timeshees.analytic_account_id.id,
            }
            expense = self.env['hr.expense'].create(data)
            expense.timesheet_id = line.timesheet_id.id
            # expense.account_analytic_id = timeshees.analytic_account_id.id
            line.timesheet_id.expense_id = expense.id
            context_vals = expense._get_default_expense_sheet_values()
            sheets = self.env['hr.expense.sheet'].create(context_vals)
            sheets.name = 'Expense Report - ' + line.timesheet_id.project_id.name
            sheetsids.append(sheets.id)

        action = self.env.ref('hr_expense.action_hr_expense_sheet_my_all')
        result = action.read()[0]
        result['domain'] = [('id', 'in', sheetsids)]
        return result

        # return {
        #     'name': _('New Expense Report'),
        #     'type': 'ir.actions.act_window',
        #     'views': [[False, "list"], [False, "form"]],
        #     'res_model': 'hr.expense.sheet',
        #     'domain': [('id', 'in', sheetsids)],
        #     'context': self.env.context,
        # }



class WizardSelectTimesheetLine(models.TransientModel):
    _name = 'wizard.select.timesheet.line'

    order_id = fields.Many2one('wizard.select.timesheet', string='Lines', ondelete='cascade')
    name = fields.Char('Description', required=False, )
    date = fields.Date('Date',
                       required=True,
                       index=True,
                       default=fields.Date.context_today, )

    user_id = fields.Many2one(
        'res.users',
        string='User',
        default=lambda self: self.env.context.get('user_id', self.env.user.id),
        index=True,
    )
    # account.analytic.line
    timesheet_id = fields.Many2one('account.analytic.line', string='Timesheet', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Category', tracking=True,
                                 domain="[('can_be_expensed', '=', True)]",
                                 ondelete='restrict')
    unit_amount = fields.Float(
        'Quantity',
        default=0.0,
    )
