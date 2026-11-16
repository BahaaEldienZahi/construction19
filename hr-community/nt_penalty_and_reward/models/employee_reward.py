# -*- coding: utf-8 -*-
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _


class EmployeeReward(models.Model):
    _name = 'employee.reward'
    _description = 'employee reward '

    name = fields.Char('Reward Name')
    description = fields.Text('Reward description')
    is_reward = fields.Boolean(default=True)
    active = fields.Boolean('Active', default=True)
    code = fields.Char('Code')
    category_id = fields.Many2one('hr.salary.rule.category', string='Category', required=True)
    struct_id = fields.Many2one('hr.payroll.structure', string='Salary Structure')
    is_time_off = fields.Boolean(default=False)
    is_vacations_instead = fields.Boolean(string='بدل أجازات')
    is_resignation = fields.Boolean(string="Is Resignation")

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
        print('month_days', month_days)
        self.env['hr.salary.rule'].sudo().create({
            "name": res.name,
            "code": res.code,
            # "struct_id": res.struct_id.id,
            "category_id": res.category_id.id,
            "amount_select": 'code',
            "amount_python_compute": _(
                'result =employee.get_total_reward_money(%s)\nemployee.get_total_reward_hour(%s)\nresult+=(employee.get_total_reward_days(%s)*contract.wage/%s)',
                res.id, res.id, res.id, month_days),
        })
        return res
