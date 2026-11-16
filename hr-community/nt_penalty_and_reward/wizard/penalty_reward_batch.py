# -*- coding: utf-8 -*-
from datetime import datetime

from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _


class PenaltyRewardBatch(models.TransientModel):
    _name = 'penalty.reward.batch'
    _description = 'Generate penalty and reward for all selected employees'

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

    department_ids = fields.Many2many('hr.department')
    employee_ids = fields.Many2many('hr.employee', compute='_compute_employees', store=True)
    start_date = fields.Date(string='From', required=True, default=start_month)
    end_date = fields.Date(string='to', required=True, default=end_month)

    def generate_penalty_reward(self):
        penalty_ids = self.env['employee.penalty'].search([])
        reward_ids = self.env['employee.reward'].search([])

        for employee_id in self.employee_ids:
            vals = {
                'employee_id': employee_id.id,
                'start_date': self.start_date,
                'end_date': self.end_date,
                'employee_penalty_ids': [(0, 0, {'penalty_id': penalty.id}) for penalty in penalty_ids],
                'employee_reward_ids': [(0, 0, {'reward_id': reward.id}) for reward in reward_ids],
            }
            self.env['employee.penalty.reward'].sudo().create(vals)
        return {
            'name': _('Your String'),
            'view_type': 'list',
            'view_mode': 'list,form,kanban',
            'res_model': 'employee.penalty.reward',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'current',
        }

    @api.depends('department_ids')
    def _compute_employees(self):
        emp_ids = []
        for rec in self.department_ids:
            for i in rec.member_ids.ids:
                emp_ids.append(i)
        for rec in self:
            rec.employee_ids = [(6, 0, emp_ids)]
