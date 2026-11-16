# -*- coding: utf-8 -*-
import datetime as dt

from datetime import datetime
from lxml import etree
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError
from odoo import models, fields, api, _
from odoo.http import request
from odoo.tools import date_utils

state = [
    ('draft', 'Draft'),
    ('submit', 'Submitted'),
    ('wait', 'Waiting for survey'),
    ('hr', 'Hr Approval'),
    ('gm', 'CEO Approval'),
    ('extend', 'Extended'),
    ('confirm', 'Confirmed'),
    ('approve', 'Approved'),
    ('done', 'Done')
]
probation_action = [
    ('0', 'Terminate'),
    ('1', 'Extend'),
    ('2', 'Employed')
]
Extend_month = [
    ('1', '1 Month'),
    ('2', '2 Month'),
    ('3', '3 Month')
]
salary_action = [
    ('new', 'Adjust salary'),
    ('old', 'Same salary')
]


class EmployeeProbationPeriod(models.Model):
    _name = 'employee.probation.period'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Employee Probation Period model'
    _rec_name = 'employee_id'

    def _compute_employee_domain(self):
        if self.env.user.employee_id.department_id.id:
            val = self.env.user.employee_id.department_id.id
            return _("[('department_id','=',%s),('in_probation_period','=',True)]", val)

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, copy=False,
                                  domain=_compute_employee_domain, tracking=True, )

    # rem_daya = fields.Integer(related='employee_id.remain_probation_period', store=True)
    rem_daya = fields.Integer(compute='_comoute_remain_days', compute_sudo=True)
    department_id = fields.Many2one('hr.department', string='Department', related='employee_id.department_id',store=True)
    survey_id = fields.Many2one('survey.survey', string='Survey', domain="[('department_ids', 'in', department_id),"
                                                                         "('is_resignation', '=', False)]",
                                tracking=True)
    is_resignation = fields.Boolean(related='survey_id.is_resignation')
    probation_action = fields.Selection(string='Probation action', selection=probation_action, tracking=True, )
    state = fields.Selection(string='State', selection=state, default='draft', tracking=True, )
    active = fields.Boolean('Active', default=True)
    extend_month = fields.Selection(string='No.of months', selection=Extend_month, tracking=True, )
    salary_action = fields.Selection(string='Salary action', selection=salary_action, tracking=True, default='old')
    old_salary = fields.Float(string='Old Salary', compute="compute_old_salary")
    new_salary = fields.Float(string='New Salary', default=0)
    date_from = fields.Date(string='Start Date')
    date_to = fields.Date(string='End Date')
    hide_approve_button = fields.Boolean(compute="compute_hide_approve_button")
    hide_draft_button = fields.Boolean(compute="compute_hide_draft_button", default=True)
    is_readonly = fields.Boolean(compute="compute_is_readonly", default=True)
    answer_done_count = fields.Integer(string='Attempts', related='survey_id.answer_done_count', store=True)
    no_of_surveys = fields.Integer(string='Completed Surveys', compute='get_number_of_completed_surveys', store=True)

    total = fields.Float(compute="_compute_total", inverse="_inverse_total")
    amount = fields.Float()

    def _comoute_remain_days(self):
        for rec in self:
            rec.rem_daya = 0
            if rec.employee_id and rec.employee_id.contract_id:
                if rec.employee_id.contract_id.state == 'open' and rec.employee_id.in_probation_period:
                    probation_date_end = rec.employee_id.probation_period_end_date
                    date_start = rec.employee_id.date_start
                    if date_start and probation_date_end:
                        date_deffer = (probation_date_end - dt.date.today()).days
                        rec.rem_daya = date_deffer
            else:
                rec.rem_daya = 0

    @api.onchange('probation_action')
    def change_action_after_extend(self):
        for rec in self:
            if rec.state == 'extend':
                if rec.probation_action != '1':
                    rec.state = 'wait'
                else:
                    rec.state = 'extend'

    @api.depends("amount")
    def _compute_total(self):
        for record in self:
            record.total = 2.0 * record.amount

    def _inverse_total(self):
        for record in self:
            record.amount = record.total / 2.0

    def compute_old_salary(self):
        for rec in self:
            if rec.employee_id and rec.employee_id.sudo().contract_id.wage > 0.0:
                rec.old_salary = rec.employee_id.sudo().contract_id.wage
            else:
                rec.old_salary = 0.0

    def compute_hide_approve_button(self):
        user = self.env.user
        if self.state == 'hr' and (
                user.has_group('national_probation_period.group_probation_period_hr_approve') or user.has_group(
            'national_probation_period.group_probation_period_gm_approve')):
            self.hide_approve_button = False
        elif self.state == 'gm' and user.has_group('national_probation_period.group_probation_period_gm_approve'):
            self.hide_approve_button = False
        else:
            self.hide_approve_button = True

    @api.depends('state')
    def compute_hide_draft_button(self):
        user = self.env.user
        for rec in self:
            if self.state == 'done' and user.has_group('national_probation_period.group_probation_period_hr_approve'):
                rec.hide_draft_button = False
            else:
                rec.hide_draft_button = True

    @api.depends('state')
    def compute_is_readonly(self):
        user = self.env.user
        for rec in self:
            if self.state == 'done':
                if user.has_group('national_probation_period.group_probation_period_hr_approve'):
                    rec.is_readonly = False
                else:
                    rec.is_readonly = True
            else:
                rec.is_readonly = False

    def action_confirm_Extend(self):
        for rec in self:
            if rec.state == 'extend' and rec.extend_month:
                rec.state = 'approve'
    def action_do_submit(self):
        # confirm salary and update
        if self.probation_action == '0':
            self.state = 'wait'

        elif self.probation_action == '1':
            self.state = 'extend'
            if self.extend_month == '1':
                self.employee_id.probation_period_end_date += relativedelta(months=1)
            elif self.extend_month == '2':
                self.employee_id.probation_period_end_date += relativedelta(months=2)
            elif self.extend_month == '3':
                self.employee_id.probation_period_end_date += relativedelta(months=3)

        elif self.probation_action == '2':
            # adjust salary
            if self.salary_action == 'new':
                self.state = 'wait'
            else:
                self.state = 'wait'

    def action_salary_approve(self):
        if self.state == 'hr':
            if self.probation_action == '2' and self.salary_action == 'new':
                self.state = 'gm'
            else:
                self.state = 'confirm'
        elif self.state == 'gm':
            self.state = 'confirm'

    def action_salary_reject(self):
        self.state = 'confirm'
        self.salary_action = 'old'

    def action_do_wait(self):
        # go to start servey if state is terminate or fix
        # self.state = 'confirm'
        request.session['emp'] = self.employee_id.id
        request.session['pid'] = self.id
        # return self.survey_id.sudo().action_test_survey()
        return self.survey_id.sudo().action_start_survey()

    @api.depends('answer_done_count', 'state', 'no_of_surveys')
    def get_number_of_completed_surveys(self):
        for rec in self:
            if rec.state == 'wait':
                if rec.no_of_surveys > 0:
                    rec.state = 'hr'
                if rec.answer_done_count > 0:
                    total_surveys = self.env['survey.user_input'].sudo().search_count(
                        [('employee_id', '=', rec.employee_id.id), ('state', '=', 'done'),
                         ('survey_id', '=', rec.survey_id.id)])
                    if total_surveys:
                        rec.no_of_surveys = total_surveys
                        # rec.state = 'hr'
                    else:
                        rec.no_of_surveys = 0
            else:
                total_surveys = self.env['survey.user_input'].sudo().search_count(
                    [('employee_id', '=', rec.employee_id.id), ('state', '=', 'done'),
                     ('survey_id', '=', rec.survey_id.id)])
                rec.no_of_surveys = total_surveys

    @api.constrains('answer_done_count', 'no_of_surveys')
    def change_state(self):
        for rec in self:
            if rec.no_of_surveys > 0 and rec.state == 'wait':
                rec.state = 'hr'

    def get_surveys(self):
        return {
            'name': _('Surveys'),
            'type': 'ir.actions.act_window',
            'res_model': 'survey.user_input',
            'view_mode': 'tree,form',
            'domain': [('employee_id', '=', self.employee_id.id), ('state', '=', 'done'),
                       ('survey_id', '=', self.survey_id.id)],
        }

    def action_do_confirm(self):
        # approve for extend an employee
        if self.probation_action == '0':
            self.employee_id.probation_period_end_date = self.date_to
            self.employee_id.contract_end_date = self.date_to
            self.employee_id.sudo().contract_id.probation_date_end = self.date_to
        if self.probation_action == '1':
            if self.extend_month == '1':
                self.employee_id.probation_period_end_date += relativedelta(months=1)
            elif self.extend_month == '2':
                self.employee_id.probation_period_end_date += relativedelta(months=2)
            elif self.extend_month == '3':
                self.employee_id.probation_period_end_date += relativedelta(months=3)
            self.state = 'done'
            self.employee_id.sudo().contract_id.probation_date_end = self.employee_id.probation_period_end_date
            month_num = int(self.extend_month)
            # probation_date_end = datetime.now().date()
            if self.employee_id.sudo().contract_id.probation_date_end:
                probation_date_end = self.employee_id.sudo().contract_id.probation_date_end + relativedelta(
                    months=+month_num)
                date_start = self.employee_id.sudo().contract_id.date_start
                date_deffer = date_start - probation_date_end

                if abs(date_deffer.days / 30) <= 6 and abs(date_deffer.days / 30) >= 1:

                    self.employee_id.sudo().contract_id.sudo().write({'probation_date_end': probation_date_end})
                else:
                    self.state = 'approve'
                    raise ValidationError("You Can't Extending More Than 6 Month From contract Start")

        elif self.probation_action == '2':
            if self.salary_action == 'new':
                current_contract = self.employee_id.sudo().contract_id
                current_contract.is_auto_allocate_timeoff = True
                current_contract.probation_date_end = False
                # if self.date_from:
                #     current_contract.date_end = self.date_from + relativedelta(days=-1)
                # else:
                #     raise ValidationError("You Have to Set Start Date")
                self.employee_id.in_probation_period = False
                self.employee_id.probation_period_end_date = False
                self.employee_id.sudo()._create_payment()
                # current_contract.write({'state': 'cancel'})
                wage = current_contract.wage + self.new_salary
                if current_contract:
                    current_contract.sudo().write({'wage': self.new_salary})
                else:
                    raise ValidationError(_("No contract for this employee"))
                # contract_id = self.env['hr.contract'].sudo().create({
                #     'name': f"{current_contract.name} ",
                #     'state': 'open',
                #     'employee_id': self.employee_id.id,
                #     'wage': self.new_salary,
                #     'date_start': datetime.now().date(),
                #     'att_policy_id': current_contract.att_policy_id.id
                # })
                # print("contract policy", contract_id['att_policy_id'])
                # current_contract_end_date = self.date_from.strftime('%Y-%m-%d')
                # new_contract_str_date = contract_id.sudo().date_start.strftime('%Y-%m-%d')
                # self.employee_id.contract_id = contract_id.id
                # current_date = str(datetime.now().date())
                # if new_contract_str_date == current_date and current_contract_end_date == current_date:
                #     current_contract.sudo().write({'state': 'cancel'})
                #     contract_id.sudo().state = 'open'

            else:
                self.employee_id.sudo().contract_id.is_auto_allocate_timeoff = True
                # self.employee_id.date_start = datetime.now().date()
                # self.employee_id.contract_id.date_start = datetime.now().date()
                self.employee_id.sudo().contract_id.probation_date_end = False
                self.employee_id.in_probation_period = False
                self.employee_id.probation_period_end_date = False
                self.employee_id.sudo()._create_payment()

            self.state = 'done'
        else:
            self.state = 'done'
            self.employee_id.sudo().contract_id.probation_date_end = self.date_to

    def action_do_approve(self):
        self.state = 'done'

    def action_do_terminate(self):
        self.state = 'terminate'

    def action_do_draft(self):
        self.state = 'draft'

    def gt_tree_ans(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'survey.user_input',
            'view_mode': 'tree',
            'target': 'current',
            'domain': [('employee_id', '=', self.employee_id.id)],
            "binding_model_id": 'survey.user_input',
            'res_id': self.id,
        }

    def _probation_reminder_job(self):
        Config = self.env['ir.config_parameter'].sudo()
        num_day_before = int(Config.get_param('national_probation_period.num_day_before')) * -1
        activity_type_id = self.env.ref('mail.mail_activity_data_todo').id
        res_model_id = self.env['ir.model'].search([('name', '=', self._description)]).id

        employees = self.env['employee.probation.period'].search([
            ('rem_day', '=', num_day_before)
        ])
        for employee in employees:
            if employee.employee_id.parent_id and employee.employee_id.parent_id.user_id:
                self.env['mail.activity'].create([{
                    'activity_type_id': activity_type_id,
                    'date_deadline': fields.Datetime.today(),
                    'summary': f"the Probation of {employee.display_name} will end soon.",
                    'user_id': employee.employee_id.parent_id.user_id.id,
                    'res_id': employee.id,
                    'res_model_id': res_model_id,
                }])

