# -*- coding: utf-8 -*-
from datetime import timedelta
import logging

from odoo import models, fields, api, _
from odoo.exceptions import AccessError, ValidationError

_logger = logging.getLogger(__name__)


class Employee(models.Model):
    _name = "hr.employee"
    _inherit = "hr.employee"

    att_user_id = fields.Char("Attendance User ID", default='0')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('att_user_id') or vals['att_user_id'] == '0':
                vals['att_user_id'] = self.env['ir.sequence'].next_by_code('hr.employee.attendance.user.id')
        return super().create(vals_list)


    @api.constrains('att_user_id')
    def _check_att_user_id(self):
        for employee in self:
            if employee.att_user_id:
                att_employee_ids = self.search(
                    [('att_user_id', '=', employee.att_user_id)])
                if len(att_employee_ids) > 1:
                    raise ValidationError('Attendance User ID Must be unique')

    def convert_log_to_attendance(self):
        self.ensure_one()
        attendance_obj = self.env['hr.attendance']
        log_obj = self.env['biometric.log']
        log_domain = [('employee_id', '=', self.id)]
        _logger.info(
            'BIO-ATTENDANCE==> Convert Biometric Log to attendnace for employee : %s' % self.name)
        prev_attendance_id = attendance_obj.search(
            [('employee_id', '=', self.id)],
            order='check_in desc', limit=1)
        if prev_attendance_id:

            if prev_attendance_id.check_out:
                log_domain += [('name', '>', prev_attendance_id.check_out)]
            else:
                log_domain += [('name', '>', prev_attendance_id.check_in)]

        log_ids = log_obj.search(log_domain, order='name asc')
        for log in log_ids:
            log_time = log.name
            prev_attendance_id = attendance_obj.search(
                [('employee_id', '=', self.id)],
                order='check_in desc', limit=1)
            min_time = log.machine.min_time
            max_time = log.machine.max_time

            if prev_attendance_id and not prev_attendance_id.check_out and log.type == 'in':
                prev_att_checkin_time = prev_attendance_id.check_in

                if min_time >= (log_time - prev_att_checkin_time):
                    continue
                else:
                    prev_attendance_id.write({
                        'check_out': prev_attendance_id.check_in,
                        'state': 'fixout'
                    })
                    new_attendance = attendance_obj.create({
                        'employee_id': self.id,
                        'check_in': log_time,
                    })
                    continue
            elif prev_attendance_id and not prev_attendance_id.check_out and log.type == 'out':
                prev_att_checkin_time = prev_attendance_id.check_in
                if max_time >= (log_time - prev_att_checkin_time):
                    prev_attendance_id.write({
                        'check_out': log_time,
                    })

                else:

                    prev_attendance_id.write({
                        'check_out': prev_att_checkin_time + timedelta(
                            milliseconds=1),
                        'state': 'fixout'
                    })

                    new_attendance = attendance_obj.create({
                        'employee_id': self.id,
                        'check_in': log_time - timedelta(milliseconds=1),
                        'check_out': log_time,
                        'state': 'fixin'

                    })

            elif prev_attendance_id and prev_attendance_id.check_out and log.type == 'in':
                prev_att_checkout_time = prev_attendance_id.check_out
                new_attendance = attendance_obj.create({
                    'employee_id': self.id,
                    'check_in': log_time,
                    'state': 'right'

                })
            elif prev_attendance_id and prev_attendance_id.check_out and log.type == 'out':
                prev_att_checkout_time = prev_attendance_id.check_out
                if min_time >= (log_time - prev_att_checkout_time):
                    prev_attendance_id.write({'check_out': log_time})

                else:
                    new_attendance = attendance_obj.create({
                        'employee_id': self.id,
                        'check_in': log_time - timedelta(milliseconds=1),
                        'check_out': log_time,
                        'state': 'fixin'

                    })

            elif not prev_attendance_id:
                new_attendance = attendance_obj.create({
                    'employee_id': self.id,
                    'check_in': log_time,
                    'state': 'right'

                })
class HrEmployeePublic(models.Model):
    _inherit = "hr.employee.public"

    att_user_id = fields.Char("Attendance User ID", default='0')