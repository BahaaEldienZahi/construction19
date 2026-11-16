# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    pr_ids = fields.One2many('employee.penalty.reward', 'employee_id')
    payslip_from = fields.Date()
    payslip_to = fields.Date()

    def get_pr_tree(self):
        ps_record = self.env['employee.penalty.reward'].search([('employee_id', '=', self.id)], limit=1)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'employee.penalty.reward',
            'view_mode': 'tree',
            'target': 'current',
            'domain': [('employee_id', '=', self.id)],
            "binding_model_id": 'employee.penalty.reward',
            'res_id': ps_record.id,
        }
    def get_total_reward_hour(self, id):
        total_reward_hour = 0
        for rec in self.pr_ids:
            if rec.state == 'approve' and rec.start_date >= self.payslip_from and rec.end_date <= self.payslip_to:
                total_reward_hour += sum(rec.employee_reward_ids.filtered(
                    lambda line: line.payment_method == 'hour' and line.reward_id.code == id).mapped(
                    'amount_hour')) or 0.0
        return total_reward_hour

    def get_total_reward_money(self, id):
        total_reward_money = 0
        for rec in self.pr_ids:
            if rec.state == 'approve' and rec.start_date >= self.payslip_from and rec.end_date <= self.payslip_to:
                total_reward_money += sum(rec.employee_reward_ids.filtered(
                    lambda line: line.payment_method == 'money' and line.reward_id.code == id).mapped(
                    'amount_money')) or 0.0
        return total_reward_money

    def get_total_penalty_money(self, id):
        total_penalty_money = 0
        for rec in self.pr_ids:
            if rec.state == 'approve' and rec.start_date >= self.payslip_from and rec.end_date <= self.payslip_to:
                total_penalty_money += sum(rec.employee_penalty_ids.filtered(
                    lambda line: line.payment_method == 'money' and line.penalty_id.code == id).mapped(
                    'amount_money'))
        return total_penalty_money

    def get_total_penalty_hour(self, id):
        total_penalty_hour = 0
        for rec in self.pr_ids:
            if rec.state == 'approve' and rec.start_date >= self.payslip_from and rec.end_date <= self.payslip_to:
                total_penalty_hour += sum(rec.employee_penalty_ids.filtered(
                    lambda line: line.payment_method == 'hour' and line.penalty_id.code == id).mapped(
                    'amount_hour'))
        return total_penalty_hour

    def get_total_reward_days(self, id):
        total_reward_days = 0
        for rec in self.pr_ids:
            if rec.state == 'approve' and rec.start_date >= self.payslip_from and rec.end_date <= self.payslip_to:
                total_reward_days += sum(rec.employee_reward_ids.filtered(
                    lambda line: line.payment_method == 'day' and line.reward_id.code == id).mapped('amount_day')) or 0.0
        return total_reward_days

    def get_total_penalty_days(self, id):
        total_penalty_days = 0
        for rec in self.pr_ids:
            if rec.state == 'approve' and rec.start_date >= self.payslip_from and rec.end_date <= self.payslip_to:
                total_penalty_days += sum(rec.employee_penalty_ids.filtered(
                    lambda line: line.payment_method == 'day' and line.penalty_id.code == id).mapped('amount_day')) or 0.0
        return total_penalty_days
class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    pr_ids = fields.One2many('employee.penalty.reward', 'employee_id')
    payslip_from = fields.Date()
    payslip_to = fields.Date()