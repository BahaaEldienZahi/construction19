from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
from lxml.builder import unicode
from odoo.exceptions import ValidationError
from datetime import datetime, date, timedelta
from odoo.http import request
from markupsafe import Markup


class Resignation(models.Model):
    _name = "hr.resignation"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _check_company_auto = True

    name = fields.Char(string='Code', readonly=True, default='New')
    employee_id = fields.Many2one('hr.employee',
                                  default=lambda self: self._default_employee(),
                                  domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]"
                                  )
    department_id = fields.Many2one('hr.department', string='Department', related='employee_id.department_id',
                                    store=True)
    resignation_date = fields.Date('Resignation Date', tracking=True)
    reason = fields.Text('Comment', tracking=True)
    reason_id = fields.Many2one(
        'resignation.reason',
        string='Resignation Reason',
        required=True,
        tracking=True
    )
    end_notice_period = fields.Date('End of notice period', compute='_compute_notice_period', tracking=True)
    last_working_day = fields.Date('Last working Day', default=lambda self: self._default_last_working_day(),
                                   compute='_compute_last_working_day', store=True, readonly=False, tracking=True)
    change_date_flag = fields.Boolean(default=False)
    new_company_name = fields.Char('New Company', tracking=True)
    new_salary = fields.Float('New Salary', tracking=True)
    new_job_title = fields.Char('New Job Title')
    active = fields.Boolean(string='Active', default=True, )
    is_clearance = fields.Boolean('Clearance')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submit', 'Submitted'),
        ('manager_approval', 'Manager Approval'),
        ('hr_confirmation', 'HR Confirmation'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
        ('cancel', 'Cancel'),
        ('rejoin', 'Rejoin'),
        ('counter_offer', 'Counter Offer'),
        ('change_date', 'Change Date'),
        ('reject', 'Reject')
    ], string='Status', readonly=True, default='draft')

    related_request = fields.Many2one('hr.resignation', string='Related request')
    resignation_date_readonly = fields.Boolean(compute='_check_user_group')
    employee_company_id = fields.Many2one('res.company', string="Employee's Company", related='employee_id.company_id')
    company_id = fields.Many2one('res.company', string="Current Company", default=lambda self: self.env.company)
    buttons_visibility = fields.Boolean(string='Visibility', default=False, compute='_compute_visibility')
    is_manager = fields.Boolean(default=False, compute='_check_manager')
    survey_id = fields.Many2one('survey.survey', string='Survey', domain="[('is_resignation', '=', True)]")
    is_resignation = fields.Boolean(related='survey_id.is_resignation')
    is_resignation_exit = fields.Boolean(related='survey_id.is_resignation_exit',string="Exit Interview")
    answer_done_count = fields.Integer(string='Attempts', related='survey_id.answer_done_count', store=True)
    answer_done_count_exit_survey = fields.Integer(string='Attempts Exit', related='exit_survey_id.answer_done_count',
                                                   store=True)
    no_of_surveys = fields.Integer(string='Completed Surveys', compute='get_number_of_completed_surveys', store=True)
    no_of_exit_surveys = fields.Integer(string='Completed Exit Surveys',
                                        compute='get_number_of_completed_exit_surveys', )
    exit_survey_id = fields.Many2one('survey.survey', string='Exit Survey',
                                     domain="[('is_resignation_exit', '=', True)]")
    plan_days = fields.Float(string='Plan', default=0.0, compute='get_number_of_plan_days')
    actual_days = fields.Float(string='Actual', default=0.0, compute='get_number_of_actual_days')
    difference_days = fields.Float(string='Diff', default=0.0, compute='get_number_of_difference_days')
    no_of_employee_penalty_reward = fields.Integer(compute='get_number_of_employee_penalty_reward', )

    def create_employee_penalty_reward(self):
        for rec in self:
            penalty_id = self.env['employee.penalty'].search([('is_resignation', '=', True)], limit=1)
            reward_id = self.env['employee.reward'].search([('is_resignation', '=', True)], limit=1)
            if not penalty_id and rec.difference_days < 0:
                raise ValidationError(_('Penalty for resignation not found.'))
            if not reward_id and rec.difference_days > 0:
                raise ValidationError(_('Reward for resignation not found.'))

            resignation_obj = self.env['employee.penalty.reward'].sudo().search([('resignation_id', '=', rec.id)])
            if resignation_obj.filtered(lambda r: r.state in ['confirm', 'approve']):
                raise ValidationError(_('You already have a penalty or reward in confirm or approve status.'))

            resignation_obj.unlink()
            if rec.difference_days < 0.0:
                self.env['employee.penalty.reward'].sudo().create({
                    'resignation_id': rec.id,
                    'employee_id': rec.employee_id.id,
                    'employee_penalty_ids': [(0, 0, {
                        'penalty_id': penalty_id.id,
                        'payment_method': 'day',
                        'amount_day': -rec.difference_days
                    })],
                })
            elif rec.difference_days > 0.0:
                self.env['employee.penalty.reward'].sudo().create({
                    'resignation_id': rec.id,
                    'employee_id': rec.employee_id.id,
                    'employee_reward_ids': [(0, 0, {
                        'reward_id': reward_id.id,
                        'payment_method': 'day',
                        'amount_day': rec.difference_days
                    })],
                })

    @api.depends('employee_id')
    def get_number_of_employee_penalty_reward(self):
        for rec in self:
            total_employee_penalty_reward = self.env['employee.penalty.reward'].sudo().search_count(
                [('employee_id', '=', rec.employee_id.id), ('resignation_id', '=', rec.id)]
            )
            rec.no_of_employee_penalty_reward = total_employee_penalty_reward

    def get_employee_penalty_reward(self):
        return {
            'name': _('Penalties & Rewards'),
            'type': 'ir.actions.act_window',
            'res_model': 'employee.penalty.reward',
            'view_mode': 'tree',
            'domain': [('employee_id', '=', self.employee_id.id), ('resignation_id', '=', self.id), ],
        }

    def get_data_allocation_and_timeoff(self):
        for rec in self:
            # ('date_from', '<=', rec.end_notice_period),
            # ('date_to', '>=', rec.end_notice_period),
            allocation_objs = self.env['hr.leave.allocation'].search(
                [('holiday_status_id.is_resignation', '=', True),
                 ('employee_id', '=', rec.employee_id.id),
                 ('state', '=', 'validate'),
                 ])
            allocation_days = sum(allocation_objs.mapped('number_of_days_display'))
            residual_allocation_days = allocation_days - rec.plan_days

            allocation_dict = {
                allocation.holiday_status_id: allocation.number_of_days_display
                for allocation in allocation_objs
            }

            time_off_dict = {}
            # end_notice_year = rec.end_notice_period.year
            # ('request_date_from', '>=', f'{end_notice_year}-01-01'),
            # ('request_date_from', '<=', f'{end_notice_year}-12-31')
            time_off_objs = self.env['hr.leave'].search([
                ('holiday_status_id.is_resignation', '=', True),
                ('employee_id', '=', rec.employee_id.id),
                ('state', '=', 'validate'),
            ])
            time_off_days = sum(time_off_objs.mapped('number_of_days_display'))
            for time_off in time_off_objs:
                holiday = time_off.holiday_status_id
                time_off_dict[holiday] = time_off_dict.get(holiday, 0) + time_off.number_of_days_display

            # Calculate difference dictionary
            difference_dict = {
                key: allocation_dict.get(key, 0) - time_off_dict.get(key, 0)
                for key in set(allocation_dict) | set(time_off_dict)
            }

            return allocation_objs, allocation_days, residual_allocation_days, time_off_objs, time_off_days, difference_dict

    def round_down_half(self, value):
        return int(value * 2) / 2.0

    @api.depends('employee_id', 'end_notice_period', 'last_working_day')
    def get_number_of_plan_days(self):
        for rec in self:
            rec.plan_days = 0.0
            allocation_objs, allocation_days, residual_allocation_days, time_off_objs, time_off_days, difference_dict = rec.get_data_allocation_and_timeoff()

            employee, start_date = rec.employee_id._get_employee_vals()

            if allocation_objs:
                for allocation in allocation_objs:
                    if start_date and rec.last_working_day:
                        if start_date.year < rec.last_working_day.year:
                            number_month_stay = relativedelta(rec.last_working_day, allocation.date_from).months + \
                                                relativedelta(rec.last_working_day, allocation.date_from).years * 12
                        else:
                            delta = relativedelta(rec.last_working_day, start_date)
                            number_month_stay = delta.years * 12 + delta.months
                            if delta.days >= 15:
                                number_month_stay += 1
                        month_off_days = 21 / 12

                        if number_month_stay > 0:
                            # rec.plan_days = round(number_month_stay * month_off_days)
                            value_days = number_month_stay * month_off_days
                            rec.plan_days = self.round_down_half(value_days)

    @api.depends('employee_id')
    def get_number_of_actual_days(self):
        for rec in self:
            rec.actual_days = 0.0

            allocation_objs, allocation_days, residual_allocation_days, time_off_objs, time_off_days, difference_dict = rec.get_data_allocation_and_timeoff()
            if time_off_objs:
                # rec.actual_days = round(time_off_days)
                rec.actual_days = self.round_down_half(time_off_days)

    @api.depends('plan_days', 'actual_days')
    def get_number_of_difference_days(self):
        for rec in self:
            rec.difference_days = rec.plan_days - rec.actual_days

    def create_time_off(self, holiday_status_id, days, request_date_from, request_date_to):
        for rec in self:
            new_leave = rec.env['hr.leave'].sudo().create({
                'holiday_status_id': holiday_status_id.id,
                # 'number_of_days': days,
                'number_of_days_display': days,
                'employee_id': rec.employee_id.id,
                'request_date_from': request_date_from,
                'request_date_to': request_date_to,
                'name': (_(
                    'This leave is due to resignation %s.')) % (rec.display_name),
            })
            # new_leave.state = 'validate'

    def get_number_of_timeoff_days(self):
        for rec in self:
            allocation_objs, allocation_days, residual_allocation_days, time_off_objs, time_off_days, difference_dict = rec.get_data_allocation_and_timeoff()
            residual_allocation = residual_allocation_days
            final_result = {}
            request_date_start = rec.last_working_day

            for holiday_status, remaining_days in difference_dict.items():
                if remaining_days > 0 and residual_allocation > 0:
                    allocated_days = min(remaining_days, residual_allocation)

                    request_date_from = request_date_start
                    request_date_to = request_date_from + timedelta(days=allocated_days - 1)

                    final_result[holiday_status] = (allocated_days, request_date_from, request_date_to)
                    residual_allocation -= allocated_days

                    request_date_start = request_date_to + timedelta(days=1)
            for holiday_status, (days, request_date_from, request_date_to) in final_result.items():
                rec.create_time_off(holiday_status, days, request_date_from, request_date_to)

    @api.depends('answer_done_count', 'no_of_surveys')
    def get_number_of_completed_surveys(self):
        for rec in self:
            total_surveys = self.env['survey.user_input'].sudo().search_count(
                [('employee_id', '=', rec.employee_id.id), ('state', '=', 'done'),
                 ('survey_id', '=', rec.survey_id.id)])
            rec.no_of_surveys = total_surveys

    @api.depends('survey_id')
    def get_number_of_completed_exit_surveys(self):
        for rec in self:
            # ('employee_id', '=', rec.employee_id.id)
            total_surveys = self.env['survey.user_input'].sudo().search_count(
                [('state', '=', 'done'),
                 ('survey_id', '=', rec.exit_survey_id.id),
                 ('partner_id.employee_ids', 'in', self.employee_id.id), ('create_date', '>=', self.resignation_date)]
            )
            rec.no_of_exit_surveys = total_surveys
            if rec.state == 'confirmed' and rec.no_of_exit_surveys >= 1:
                rec.state = 'done'

    def get_surveys(self):
        return {
            'name': _('Surveys'),
            'type': 'ir.actions.act_window',
            'res_model': 'survey.user_input',
            'view_mode': 'tree,form',
            'domain': [('employee_id', '=', self.employee_id.id), ('state', '=', 'done'),
                       ('survey_id', '=', self.survey_id.id)],
        }

    def get_exit_interview_result(self):
        return {
            'name': _('Exit Interview Result'),
            'type': 'ir.actions.act_window',
            'res_model': 'survey.user_input',
            'view_mode': 'tree,form',
            'domain': [('partner_id.employee_ids', 'in', self.employee_id.id), ('state', '=', 'done'),
                       ('survey_id', '=', self.exit_survey_id.id), ('create_date', '>=', self.resignation_date)],
        }

    def gt_tree_ans(self):
        # ps_record = self.env['survey.user_input'].search([('employee_id', '=', self.employee_id.id)], limit=1)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'survey.user_input',
            'view_mode': 'tree',
            'target': 'current',
            'domain': [('employee_id', '=', self.employee_id.id)],
            "binding_model_id": 'survey.user_input',
            'res_id': self.id,
        }

    @api.model
    def _default_employee(self):
        return self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1)

    @api.depends('state')
    def _compute_last_working_day(self):
        for rec in self:
            if not rec.last_working_day:
                rec.last_working_day = rec.end_notice_period
            else:
                return

    def change_date(self):
        self.change_date_flag = True

    def _send_hr_email(self):
        hr_users = self.env.ref('nt_resignation.group_resignation_hr').users
        partner_ids = hr_users.mapped('partner_id').ids
        if not partner_ids:
            return

        for rec in self:
            rec.message_subscribe(partner_ids=partner_ids)

            body = Markup("""
                <div style="font-family: Arial, sans-serif;">
                    <p>Dear HR Team,</p>
                    <p>A new resignation request has been submitted:</p>
                    <ul style="list-style-type: disc; padding-left: 20px;">
                        <li><strong>Employee:</strong> {}</li>
                        <li><strong>Request:</strong> {}</li>
                        <li><strong>Reason:</strong> {}</li>
                    </ul>
                    <p>Please review and take necessary action.</p>
                </div>
            """).format(rec.employee_id.name, rec.name, rec.reason_id or 'N/A')

            rec.message_post(
                subject="Resignation Request - {}".format(rec.employee_id.name),
                body=body,
                partner_ids=partner_ids,
                message_type="notification",
                subtype_xmlid="mail.mt_note",

            )

    def _notify_employee_inbox(self):
        for rec in self:
            partner = rec.employee_id.user_id.partner_id
            if not partner:
                continue

            rec.message_post(
                subject=_("Resignation Submitted"),
                body=_("Your resignation request (%s) has been submitted and is pending Manager approval.") % rec.name,
                partner_ids=[partner.id],
                message_type="notification",
                subtype_xmlid="mail.mt_note",
                author_id=partner.id,
            )

    @api.model_create_multi
    def create(self, vals):
        """
            Override create method
             - sequence name
        """
        for val in vals:
            if val.get('name', 'New') == 'New':
                val['name'] = self.env['ir.sequence'].next_by_code(
                    'hr.resignation') or '/'

            resignation_date = val.get('resignation_date')
            computed_end_notice = False
            if resignation_date:
                computed_end_notice = (datetime.strptime(str(resignation_date), '%Y-%m-%d') +
                                       relativedelta(months=2)).date()

            domain = [
                ('employee_id', '=', val.get('employee_id')),
                ('state', 'not in', ['reject', 'rejoin', 'counter_offer']),
            ]
            if resignation_date and computed_end_notice:
                domain += [
                    '|',
                    '&', ('resignation_date', '<=', resignation_date), ('end_notice_period', '>=', resignation_date),
                    '&', ('resignation_date', '<=', computed_end_notice), ('end_notice_period', '>=', computed_end_notice),
                ]

            resignation_records = self.search(domain)
            if resignation_records:
                raise ValidationError(
                    _('You have already created a resignation in this period, you can not create another one.'))

        return super(Resignation, self).create(vals)

    @api.depends('state')
    def _compute_visibility(self):
        for rec in self:
            user = self.env.user
            rec.buttons_visibility = False
            if rec.state == 'manager_approval':
                if user.has_group('nt_resignation.group_resignation_manger'):
                    if rec.employee_id == user.employee_id:
                        rec.buttons_visibility = False
                    else:
                        rec.buttons_visibility = True

    # @api.constrains('last_working_day')
    # def change_last_working_day(self):
    #     for rec in self:
    #         rec.change_date_flag = False

    def write(self, vals):
        if vals.get('last_working_day', False):
            vals["change_date_flag"] = False
        return super(Resignation, self).write(vals)

    @api.depends('resignation_date')
    def _compute_notice_period(self):
        for rec in self:
            if rec.resignation_date:
                rec.end_notice_period = (datetime.strptime(str(self.resignation_date), '%Y-%m-%d') +
                                         relativedelta(months=2)).strftime('%Y-%m-%d')
            else:
                rec.end_notice_period = None

    def action_cancel(self):
        """"cancel action if request didnt approved direct to cancel"""
        if self.state not in ['confirmed']:
            self.state = 'cancel'
            return

        else:
            return {
                'name': _('Rejoin'),
                'type': 'ir.actions.act_window',
                'res_model': 'hr.resignation.cancel',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_resignation_id': self.id
                }
            }

    def action_reject(self):
        self.state = 'reject'

    def action_draft(self):
        self.state = 'draft'
    def action_done(self):
        for rec in self:
            if rec.is_resignation_exit and rec.is_clearance:
                rec.state = 'done'
            else:
                raise ValidationError(
                    "- Exit Interview must be confirmed.\n"
                    "- Clearance process must be completed.")


    def get_employee_clearance(self):
        self.ensure_one()

        clearance = self.env['clearance.request'].search([
            ('resignation_id', '=', self.id)
        ], limit=1)

        if not clearance:
            return ValidationError('Not Find Clearance For This Employee')

        return {
            'type': 'ir.actions.act_window',
            'name': 'Employee Clearance',
            'res_model': 'clearance.request',
            'view_mode': 'form',
            'res_id': clearance.id,
            'target': 'current',
        }
    def action_do_exit_interview(self):
        for rec in self:
            rec.sudo().message_post_with_source('nt_resignation.template_of_exit_interview_email', **{
                'subtype_id': rec.env['ir.model.data']._xmlid_to_res_id('mail.mt_note'),
                'email_layout_xmlid': 'mail.mail_notification_light',
            })

    @api.model
    def _default_last_working_day(self):
        return self.end_notice_period

    def _check_user_group(self):
        for rec in self:
            user = self.env.user
            if user.has_group('nt_resignation.group_resignation_user'):
                if not (user.has_group('nt_resignation.group_resignation_manger') or user.has_group(
                        'nt_resignation.group_resignation_hr') or user.has_group(
                    'nt_resignation.group_resignation_admin')):
                    rec.resignation_date_readonly = True
                else:
                    rec.resignation_date_readonly = False

    @api.onchange('last_working_day')
    def _onchange_employee_contract_end_date(self):
        for rec in self:
            if rec.state == 'confirmed':
                emp = rec.employee_id
                contract_id = emp.sudo().contract_id
                if not contract_id:
                    raise ValidationError('selected employee does not has active contract ')
                if not rec.last_working_day:
                    raise ValidationError(_('last working day must be submit'))
                else:
                    contract_id.write({'date_end': rec.last_working_day})
                    emp.write({'contract_end_date': rec.last_working_day})

    def _check_manager(self):
        for rec in self:
            user = self.env.user
            rec.is_manager = False
            if user.has_group('nt_resignation.group_resignation_manger') and rec.state == 'manager_approval':
                rec.is_manager = True
            else:
                rec.is_manager = False

    def action_submit(self):
        self.update_followers()

        self._send_hr_email()
        self.state = 'manager_approval'

    def action_manager_approve(self):
        self._send_hr_email()
        self._notify_employee_inbox()
        self.state = 'manager_approval'

    def action_hr_confirm(self):
        self._notify_employee_inbox()
        self.state = 'hr_confirmation'

    def action_confirm(self):
        emp = self.sudo().employee_id
        contract = self.env['hr.contract'].search([
            ('employee_id', '=', emp.id),
            ('state', '=', 'open'),
        ], limit=1)

        if not contract:
            raise ValidationError(_("Selected employee does not have an active contract."))
        if not self.last_working_day:

            raise ValidationError(_('last working day must be submit'))
        else:
            contract.write({'date_end': self.last_working_day})
            emp.write({'contract_end_date': self.last_working_day})
            self.state = 'confirmed'
            emp.is_resigned = True
            # self.get_number_of_timeoff_days()
            # emp.contract_end_date = self.last_working_day
        Clearance = self.env['clearance.request'].sudo()
        clearance = Clearance.search([('resignation_id', '=', self.id)], limit=1)

        if not clearance:
            clearance = Clearance.create({'resignation_id': self.id})
        else:
            if not clearance.line_ids:
                clearance._generate_lines_from_setup()

    def action_do_wait_survey(self):
        # go to start servey if state is terminate or fix
        # self.state = 'confirm'
        request.session['emp'] = self.employee_id.id
        request.session['pid'] = self.id
        # return self.survey_id.sudo().action_test_survey()
        if self.survey_id:
            return self.survey_id.sudo().action_start_survey()
        else:
            raise ValidationError(
                _('You Can Not Start Survey , Please Select Survey First.'))

    def update_followers(self):
        ResignationFollowers = self.env['mail.followers']
        Group = self.env['res.groups']
        FollowerPartnerIds = ResignationFollowers.search([
            ('res_model', '=', 'hr.resignation'),
            ('res_id', '=', self.id)
        ]).mapped('partner_id.id')

        hr_group = Group.search([('id', '=', self.env.ref('nt_resignation.group_resignation_hr').id)], limit=1)
        if hr_group:
            for usr in hr_group.users:
                if usr.partner_id.id not in FollowerPartnerIds:
                    ResignationFollowers.sudo().create({
                        "res_model": "hr.resignation",
                        "res_id": self.id,
                        "partner_id": usr.partner_id.id,
                    })

    @api.model
    def _cron_notify_hr_and_employee_by_last_working_day(self):
        """create ticket according to boarding stages in recruitment"""
        self.env.registry.clear_cache()
        today = date.today()
        today_date = fields.Date.from_string(today)
        hr_resignation_obj = self.env['hr.resignation'].search([('state', '=', 'confirmed'),
                                                                ('last_working_day', '=', today_date)])
        if hr_resignation_obj:
            for res in hr_resignation_obj:
                model_id = self.env['ir.model']._get(self._name)
                employee_user = self.env.ref('nt_resignation.group_resignation_user').users
                hr_user = self.env.ref('nt_resignation.group_resignation_hr').users
                activity_type = self.env['mail.activity.type'].search([('name', '=', 'To Do')], limit=1)
                for employee in employee_user:
                    if employee.id == res.employee_id.user_id.id:
                        todos = {
                            'res_id': res.id,
                            'res_model': 'hr.resignation',
                            'res_model_id': model_id.id,
                            'user_id': employee.id,
                            'summary': 'Please Submit The Exit Survey',
                            'activity_type_id': activity_type.id,
                            'date_deadline': datetime.now().date(),
                        }
                        self.env['mail.activity'].sudo().create(todos)

                        for hr in hr_user:
                            todoss = {
                                'res_id': res.id,
                                'res_model': 'hr.resignation',
                                'res_model_id': model_id.id,
                                'user_id': hr.id,
                                'summary': 'Today is the Last Working Day for the employee for the exit survey' +
                                           unicode(employee.name),
                                'activity_type_id': activity_type.id,
                                'date_deadline': datetime.now().date(),
                            }
                            self.env['mail.activity'].sudo().create(todoss)
