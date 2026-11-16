# -*- coding: utf-8 -*-
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

state = [
    ('draft', 'Draft'),
    ('confirm', 'Confirmed'),
    ('approve', 'Approved'),
    ('rej', 'Rejected'),
]


class EmployeePenaltyReward(models.Model):
    _name = 'employee.penalty.reward'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'employee penalty and reward '
    _rec_name = 'employee_id'

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

    start_date = fields.Date(string='From', required=True, default=start_month)
    end_date = fields.Date(string='to', required=True, default=end_month)

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    employee_reward_ids = fields.One2many('reward', 'employee_reward_id')
    employee_penalty_ids = fields.One2many('penalty', 'employee_penalty_id')
    state = fields.Selection(string='State', selection=state, default='draft')
    active = fields.Boolean('Active', default=True)
    total_penalty_days = fields.Float('Penalty Days', compute='_compute_total_amount_ps', store=True)
    total_penalty_money = fields.Float('Penalty Money', compute='_compute_total_amount_ps', store=True)
    total_penalty_hours = fields.Float('Penalty Hours', compute='_compute_total_amount_ps', store=True)
    total_reward_hours = fields.Float('Reward Hours', compute='_compute_total_amount_ps', store=True)
    total_reward_days = fields.Float('Reward Days', compute='_compute_total_amount_ps', store=True)
    total_reward_money = fields.Float('Reward Money', compute='_compute_total_amount_ps', store=True)
    days_to_money = fields.Float('Time Off to Money', compute='_compute_total_amount_ps', store=True)
    # allocation_display = fields.Char('Leave Balance', related="employee_id.allocation_display", store=True)
    # allocation_used_display = fields.Char('Used Leave', related="employee_id.allocation_used_display", store=True)
    remaining_leaves = fields.Float('Remaining Leaves', related="employee_id.remaining_leaves")
    resignation_id = fields.Many2one(
        'hr.resignation',
        string="Resignation"
    )

    @api.onchange("employee_reward_ids")
    def _vacations_instead(self):
        for rec in self:
            for line in rec.employee_reward_ids:
                if line.reward_id.is_vacations_instead:
                    line.amount_money = rec.remaining_leaves * (rec.employee_id.contract_id.average_salary /30 )

    @api.onchange("employee_penalty_reward_ids")
    def _onchange_payment_method(self):
        for rec in self.employee_penalty_reward_ids:
            if rec.payment_method == 'money':
                rec.amount_day = 0
            elif rec.payment_method == 'day':
                rec.amount_money = 0.0
            else:
                rec.amount_day = 0
                rec.amount_money = 0.0

    def minus_allocation(self, days):
        for rec in self:
            allocation_id = rec.env['hr.leave.allocation'].search(
                [('employee_id', '=', rec.employee_id.id), ('holiday_status_id.time_type', '=', 'leave')])[1]

            holiday_status_id = allocation_id.holiday_status_id
            new_leave = rec.env['hr.leave'].create({
                'holiday_status_id': holiday_status_id.id,
                'number_of_days': days,
                'employee_id': rec.employee_id.id,
            })
            new_leave.state = 'validate'

    @api.depends('employee_penalty_ids', 'employee_reward_ids')
    def _compute_total_amount_ps(self):
        for rec in self:
            rec.total_penalty_days = sum(
                rec.employee_penalty_ids.filtered(lambda line: line.payment_method == 'day').mapped(
                    'amount_day')) or 0.0
            rec.total_reward_days = sum(
                rec.employee_reward_ids.filtered(
                    lambda line: line.payment_method == 'day' and not line.reward_id.is_time_off).mapped(
                    'amount_day')) or 0.0
            rec.total_penalty_money = sum(
                rec.employee_penalty_ids.filtered(lambda line: line.payment_method == 'money').mapped(
                    'amount_money')) or 0.0
            rec.total_reward_money = sum(
                rec.employee_reward_ids.filtered(lambda line: line.payment_method == 'money').mapped(
                    'amount_money')) or 0.0
            target_reward = rec.employee_reward_ids.filtered(
                lambda line: line.payment_method == 'day' and line.reward_id.is_time_off).mapped('amount_day')
            rec.days_to_money = target_reward[0] if target_reward else 0.0
            rec.total_penalty_hours = sum(
                rec.employee_penalty_ids.filtered(lambda line: line.payment_method == 'hour').mapped(
                    'amount_hour')) or 0.0
            rec.total_reward_hours = sum(
                rec.employee_reward_ids.filtered(lambda line: line.payment_method == 'hour').mapped(
                    'amount_hour')) or 0.0

    def action_do_confirm(self):
        if self.employee_penalty_ids or self.employee_reward_ids:
            self.state = state[1][0]
            model_id = self.env['ir.model']._get(self._name)
            admin_users = self.env.ref('nt_penalty_and_reward.group_penalty_reward_admin').users
            activity_type = self.env['mail.activity.type'].search([('name', '=', 'To Do')], limit=1)
            for admin in admin_users:
                todos = {
                    'res_id': self.id,
                    'res_model_id': model_id.id,
                    'user_id': admin.id,
                    'summary': 'approve P&S',
                    'activity_type_id': activity_type.id,
                    'date_deadline': datetime.now().date(),
                }
                self.env['mail.activity'].sudo().create(todos)


            target_reward = self.employee_reward_ids.filtered(
                lambda line: line.payment_method == 'day' and line.reward_id.is_time_off)
            if target_reward and self.remaining_leaves:
                number_of_days = target_reward[0].amount_day
                # if yes
                if number_of_days:
                    # get the day money value from contract
                    # money_for_one_day = self.employee_id.contract_id.leave_value

                    # apply rule to add money to payroll (money of one day * days)
                    # remove days from employee days off by minus
                    self.minus_allocation(number_of_days)

                # if no do nothing
                else:
                    print('no value in days')
            else:
                print('no reward off')
        else:
            raise ValidationError("Can't Confirm Without Penalty Or Reward")

    def action_do_approve(self):
        self.state = state[2][0]
        model_id = self.env['ir.model']._get(self._name)
        if self.employee_id.user_id:
            user = self.employee_id.user_id
            activity_type = self.env['mail.activity.type'].search([('name', '=', 'To Do')], limit=1)
            todos = {
                'res_id': self.id,
                'res_model_id': model_id.id,
                'res_model':'employee.penalty.reward',
                'user_id': user.id,
                'summary': 'Penalty',
                'activity_type_id': activity_type.id,
                'date_deadline': datetime.now().date(),
            }
            self.env['mail.activity'].sudo().create(todos)

    def action_do_draft(self):
        self.state = state[0][0]

    penalty_reward_refuse_reason = fields.Text(string="Refuse Reason")

    def reason_wizard(self, context=None):
        return {
            'name': ('Refuse Reason'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'penalty.reward.refuse.reason',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'new'
        }
