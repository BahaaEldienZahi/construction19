# -*- coding: utf-8 -*-
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _


class EmployeePenalty(models.Model):
    _name = 'employee.penalty'
    _description = 'employee penalty'

    name = fields.Char('Penalty Name')
    description = fields.Text('Penalty description')
    is_penalty = fields.Boolean(default=True)
    active = fields.Boolean('Active', default=True)
    code = fields.Char('Code')
    category_id = fields.Many2one('hr.salary.rule.category', string='Category', required=True)
    struct_id = fields.Many2one('hr.payroll.structure', string='Salary Structure')
    is_resignation = fields.Boolean(default=False)

    def start_month(self):
        date_from = datetime.now()
        if date_from.day > 25:
            date_from = (date_from - relativedelta(months=1)).replace(day=25)
        elif date_from.day < 25:
            date_from = (date_from - relativedelta(months=1)).replace(day=25)
        else:
            date_from = date_from.replace(day=25)
        return date_from

    def end_month(self):
        date_to = datetime.now()
        if date_to.day > 25:
            date_to = (date_to + relativedelta(months=1)).replace(day=24)
        if date_to.day < 25:
            date_to = date_to.replace(day=24)
        else:
            date_to = (date_to + relativedelta(months=1)).replace(day=24)
        return date_to

    @api.model
    def create(self, vals):
        res = super().create(vals)
        month_days = self.end_month() - self.start_month()
        rule = self.env['hr.salary.rule'].sudo().create({
            "name": res.name,
            "code": res.code,
            # "struct_id": res.struct_id.id,
            "category_id": res.category_id.id,
            "amount_select": 'code',
            "amount_python_compute": _(
                'result =employee.get_total_penalty_money(%s)\nemployee.get_total_penalty_hour(%s)\nresult+=(employee.get_total_penalty_days(%s)*contract.wage/%s)',
                res.id, res.id, res.id, month_days),
        })
        existing = self.env['employee.category'].search([('name', '=', res.name)], limit=1)
        if not existing:
            self.env['employee.category'].create({
                'name': res.name,
                'penalty_id': res.id,
            })
        else:
            existing.penalty_id = res.id

        return res
