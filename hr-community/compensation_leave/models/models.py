# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta


class ResourceMixin(models.AbstractModel):
    _inherit = "resource.mixin"


class LeaveType(models.Model):
    _inherit = 'hr.leave.type'

    compensation = fields.Boolean("Compensation")
    to_be_compensation = fields.Boolean("TO be compensated")


class LeaveRequest(models.Model):
    _inherit = 'hr.leave'

    to_be_compensation = fields.Boolean(related='holiday_status_id.to_be_compensation')
    compensation_type = fields.Selection([('leave', 'Leave Balance'), ('money', 'Money'),('leave_money', 'Leave Balance and Money')])
    amount = fields.Float()

    @api.depends('date_from', 'date_to', 'resource_calendar_id', 'holiday_status_id.request_unit')
    def _compute_duration(self):
        for holiday in self:
            days, hours = holiday._get_duration()
            holiday.number_of_hours = hours
            holiday.number_of_days = days
            if holiday.number_of_days == 0:
                if holiday.holiday_status_id.to_be_compensation:
                    if (holiday.date_to - holiday.date_from).days + 1 > 0:
                        holiday.number_of_days = (holiday.date_to - holiday.date_from).days + 1

    @api.model
    def _get_duration(self, check_leave_type=True, resource_calendar=None):
        """

        """
        self.ensure_one()
        days, hours = (0, 0)
        if self.holiday_status_id.is_permission:
            duration_delta = self.date_to - self.date_from
            total_seconds = max(duration_delta.total_seconds(), 0)
            hours = total_seconds / 3600
            days = hours / 24
            if self.request_hour_from and self.request_hour_to:
                if hours <= 0:
                    raise ValidationError('Hours To must be after Hours From ')
            return (days, hours)
        else:
            return super(LeaveRequest, self)._get_duration()

    def _validate_leave_request(self):
        """ Validate time off requests (holiday_type='employee')
        by creating a calendar event and a resource time off. """
        holidays = self.filtered(lambda request: request.holiday_type == 'employee' and request.employee_id)
        holidays._create_resource_leave()
        meeting_holidays = holidays.filtered(lambda l: l.holiday_status_id.create_calendar_meeting)
        meetings = self.env['calendar.event'].sudo()
        if meeting_holidays:
            meeting_values_for_user_id = meeting_holidays._prepare_holidays_meeting_values()
            Meeting = self.env['calendar.event']
            for user_id, meeting_values in meeting_values_for_user_id.items():
                meetings += Meeting.with_user(user_id or self.env.uid).with_context(
                    allowed_company_ids=[],
                    no_mail_to_attendees=True,
                    calendar_no_videocall=True,
                    active_model=self._name
                ).sudo().create(meeting_values)
        Holiday = self.env['hr.leave']
        for meeting in meetings:
            Holiday.sudo().browse(meeting.res_id).meeting_id = meeting

    @api.constrains('holiday_status_id')
    def get_companstion(self):

        if self.holiday_status_id.to_be_compensation:
            working_days = []
            for l in self.employee_id.resource_calendar_id.attendance_ids:
                working_days.append(l.dayofweek)

            if self.employee_id.resource_calendar_id:

                for i in range(0, int(self.number_of_days)):

                    check = False

                    global_ids = self.env['resource.calendar.leaves'].search(
                        [('calendar_id', '=', self.employee_id.resource_calendar_id.id),
                         ('resource_id', '=', False)])
                    timeoff_ids = self.env['resource.calendar.leaves'].search(
                        [('calendar_id', '=', self.employee_id.resource_calendar_id.id),
                         ('resource_id', '!=', False)])
                    check = False
                    weekend = False
                    public_holiday = False
                    if global_ids:
                        for rec in global_ids:
                            delta = self.request_date_to - self.request_date_from
                            for d in range(delta.days + 1):
                                work_days = self.request_date_from + timedelta(days=d)
                                if self.get_dat_num(work_days) not in working_days:
                                    weekend = True
                                if rec.date_from.date() <= work_days <= rec.date_to.date():
                                    public_holiday = True
                            if weekend and public_holiday:
                                raise ValidationError("You have to create a separate requests for public holiday")
                            if rec.date_from.date() <= self.request_date_from + timedelta(
                                    days=i) <= rec.date_to.date() or self.get_dat_num(
                                self.request_date_from + timedelta(days=i)) not in working_days:
                                check = True
                                return
                            else:
                                check = False
                    if timeoff_ids:
                        for rec in timeoff_ids:

                            if rec.date_from.date() <= self.request_date_from + timedelta(
                                    days=i) <= rec.date_to.date() or self.get_dat_num(
                                self.request_date_from + timedelta(days=i)) in working_days:
                                check = False
                            else:
                                check = True

                    if check:
                        return

                    if self.get_dat_num(self.request_date_from + timedelta(days=i)) in working_days and check == False:
                        raise ValidationError("You Can't create compensation Leave at Working Day")

    def action_approve(self):
        res = super(LeaveRequest, self).action_approve()
        for record in self:
            if record.holiday_status_id.to_be_compensation and record.compensation_type == 'leave':
                leave_type_id = self.env['hr.leave.type'].search([('compensation', '=', True)])
                if not leave_type_id:
                    raise ValidationError("please Select Type of compensation Leave ")

            if record.holiday_status_id.to_be_compensation:
                leave_type_id = self.env['hr.leave.type'].search([('compensation', '=', True)], limit=1)
                if not leave_type_id:
                    raise ValidationError(
                        "Please configure Compensation Leave Type (hr.leave.type with compensation=True)")
                record.amount = 0
                if record.compensation_type == 'money':
                    if record.employee_id.resource_calendar_id:
                        for i in range(0, int(record.number_of_days)):
                            day = record.request_date_from + timedelta(days=i)
                            existing_attendance = self.env['hr.attendance'].search([
                                ('employee_id', '=', record.employee_id.id),
                                ('check_in', '>=', datetime.combine(day, datetime.min.time())),
                                ('check_in', '<=', datetime.combine(day, datetime.max.time())),
                            ], limit=1)
                            if existing_attendance:
                                continue

                            if not existing_attendance:
                                self.env['hr.attendance'].sudo().create({
                                    'employee_id': record.employee_id.id,
                                    'check_in': datetime.combine(day, datetime.min.time()),
                                    'check_out': datetime.combine(day, datetime.min.time()) +
                                                 timedelta(hours=record.employee_id.resource_calendar_id.hours_per_day)
                            })
                            check = False
                            global_ids = self.env['resource.calendar.leaves'].search(
                                [('calendar_id', '=', record.employee_id.resource_calendar_id.id),
                                 ('resource_id', '=', False)])
                            if global_ids:
                                for rec in global_ids:
                                    if rec.date_from.date() <= record.request_date_from + timedelta(
                                            days=i) <= rec.date_to.date():
                                        record.amount += 2
                                        check = True
                            check_day = False
                            for l in record.employee_id.resource_calendar_id.attendance_ids:
                                if record.get_dat_num(record.request_date_from + timedelta(days=i)) == l.dayofweek:
                                    check_day = True
                            if check == False and check_day == False:
                                record.amount += 2

                elif record.compensation_type == 'leave':
                    allocate_id = self.env['hr.leave.allocation'].create({
                        'name': 'compensation Day instead of ' + str(record.date_from),
                        'holiday_status_id': leave_type_id.id,
                        'holiday_type': 'employee',
                        'number_of_days': record.number_of_days * 2,
                        'employee_id': record.employee_id.id
                    })
                    if record.employee_id.resource_calendar_id:
                        for i in range(0, int(record.number_of_days)):
                            day = record.request_date_from + timedelta(days=i)
                            self.env['hr.attendance'].sudo().create({
                                'employee_id': record.employee_id.id,
                                'check_in': datetime.combine(day, datetime.min.time()),
                                'check_out': datetime.combine(day, datetime.min.time()) +
                                             timedelta(hours=record.employee_id.resource_calendar_id.hours_per_day)
                            })
                    return allocate_id.action_validate()

                elif record.compensation_type == 'leave_money':
                    if record.employee_id.resource_calendar_id:
                        for i in range(0, int(record.number_of_days)):
                            day = record.request_date_from + timedelta(days=i)
                            existing_attendance = self.env['hr.attendance'].search([
                                ('employee_id', '=', record.employee_id.id),
                                ('check_in', '>=', datetime.combine(day, datetime.min.time())),
                                ('check_in', '<=', datetime.combine(day, datetime.max.time())),
                            ], limit=1)
                            if existing_attendance:
                                continue
                            if not existing_attendance:
                                self.env['hr.attendance'].sudo().create({
                                    'employee_id': record.employee_id.id,
                                    'check_in': datetime.combine(day, datetime.min.time()),
                                    'check_out': datetime.combine(day, datetime.min.time()) +
                                                 timedelta(hours=record.employee_id.resource_calendar_id.hours_per_day)
                                })
                                check = False
                            global_ids = self.env['resource.calendar.leaves'].search(
                                [('calendar_id', '=', record.employee_id.resource_calendar_id.id),
                                 ('resource_id', '=', False)])
                            if global_ids:
                                for rec in global_ids:
                                    if rec.date_from.date() <= record.request_date_from + timedelta(
                                            days=i) <= rec.date_to.date():
                                        record.amount += 2
                                        check = True
                            check_day = False
                            for l in record.employee_id.resource_calendar_id.attendance_ids:
                                if record.get_dat_num(record.request_date_from + timedelta(days=i)) == l.dayofweek:
                                    check_day = True
                            if check == False and check_day == False:
                                record.amount += 2
                    allocate = self.env['hr.leave.allocation'].create({
                        'name': 'compensation Day instead of ' + str(record.date_from),
                        'holiday_status_id': leave_type_id.id,
                        'holiday_type': 'employee',
                        'number_of_days': record.number_of_days,
                        'employee_id': record.employee_id.id
                    })
                    return allocate.action_validate()
        return res

    def get_dat_num(self, date):
        day = date.strftime("%A")
        if day == 'Monday':
            return '0'
        elif day == 'Tuesday':
            return '1'
        elif day == 'Wednesday':
            return '2'
        elif day == 'Thursday':
            return '3'
        elif day == 'Friday':
            return '4'
        elif day == 'Saturday':
            return '5'
        elif day == 'Sunday':
            return '6'
