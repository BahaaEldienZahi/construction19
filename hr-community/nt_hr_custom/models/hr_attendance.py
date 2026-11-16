from odoo import models, api
from datetime import datetime, time
import pytz

class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    @api.depends('check_in', 'check_out', 'employee_id')
    def _compute_overtime_hours(self):
        for att in self:
            if not att.check_in or not att.check_out or not att.employee_id:
                att.overtime_hours = 0.0
                continue

            employee = att.employee_id
            calendar = employee.resource_calendar_id \
                       or employee.company_id.resource_calendar_id

            if not calendar:
                att.overtime_hours = 0.0
                continue

            tz_name = calendar.tz or 'UTC'
            tz = pytz.timezone(tz_name)

            check_in_local  = pytz.utc.localize(att.check_in).astimezone(tz)
            check_out_local = pytz.utc.localize(att.check_out).astimezone(tz)

            day_of_week = str(check_in_local.weekday())

            day_lines = calendar.attendance_ids.filtered(
                lambda a: a.dayofweek == day_of_week
                and a.day_period != 'break'
            )

            if not day_lines:
                att.overtime_hours = 0.0
                continue

            shift_end_hour = max(float(line.hour_to) for line in day_lines)
            shift_end_h = int(shift_end_hour)
            shift_end_m = int(round((shift_end_hour % 1) * 60))

            shift_end = tz.localize(datetime.combine(
                check_in_local.date(),
                time(shift_end_h, shift_end_m)
            ))

            overtime_seconds = (check_out_local - shift_end).total_seconds()
            att.overtime_hours = max(overtime_seconds / 3600.0, 0.0)