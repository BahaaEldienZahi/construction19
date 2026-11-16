# -*- coding: utf-8 -*-
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _, exceptions
from odoo.exceptions import UserError


class AttendanceSheet(models.Model):
    _inherit = 'attendance.sheet'

    late_penalty_days = fields.Integer(string="Late Penalty Days")
    penalty_reward_id = fields.Many2one(comodel_name="employee.penalty.reward")

    def action_draft(self):
        self.write({'state': 'draft', 'late_penalty_days': 0})
        self.penalty_reward_id.sudo().unlink()

    def action_confirm(self):
        for rec in self:
            num_of_days = 0
            late_time_av = self.company_id.late_time_by_month
            for line in rec.line_ids.filtered(lambda l: l.late_in > 0):
                late_time_av -= (line.act_late_in * 60)
                if late_time_av < 0:
                    if (line.act_late_in * 60) >= 15:
                        num_of_days += 1
            rec.late_penalty_days = num_of_days
        return super(AttendanceSheet, self).action_confirm()

    def create_penalty_reward(self):
        for rec in self:
            if rec.late_penalty_days:
                rec.penalty_reward_id = self.env['employee.penalty.reward'].create({
                    'employee_id': rec.employee_id.id,
                    'start_date': rec.date_from,
                    'end_date': rec.date_to,
                    'employee_penalty_ids': [(0, 0, {
                        'penalty_id': self.company_id.late_time_penalty_id.id,
                        'payment_method': 'day',
                        'amount_day': rec.late_penalty_days * float(self.company_id.penalty_days),
                    })]
                }).id
            else:
                total_act_late = sum(l.act_late_in for l in rec.line_ids) * 60
                amount = 0
                if 0 < total_act_late <= 49:
                    amount = 50
                elif total_act_late >= 50:
                    amount = 0
                    raise UserError(_(
                        'This Employee Exceeds His Late Time By Month , No reward will created'))
                else:
                    amount = 100
                rec.penalty_reward_id = self.env['employee.penalty.reward'].create({
                    'employee_id': rec.employee_id.id,
                    'start_date': rec.date_from,
                    'end_date': rec.date_to,
                    'employee_reward_ids': [(0, 0, {
                        'reward_id': self.company_id.late_time_reward_id.id,
                        'payment_method': 'money',
                        'amount_money': amount,
                    })]
                }).id
