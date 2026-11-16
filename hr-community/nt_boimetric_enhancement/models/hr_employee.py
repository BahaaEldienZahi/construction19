from datetime import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api

class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    state = fields.Selection(selection=[('fixin', 'Fix'), ('fixout', 'Fix'), ('right', 'Right')],)



class HrEmployee(models.Model):
    _inherit = "hr.employee"

    def compute_log_to_domain(self):
        self.ensure_one()
        log_obj = self.env['biometric.log']
        log_domain = [('employee_id', '=', self.id)]
        max_ever = log_obj.search(log_domain, order='name desc', limit=1)
        min_ever = log_obj.search(log_domain, order='name asc', limit=1)
        # min_ever = log_obj.search(log_domain, order='name desc', limit=1).name + relativedelta(months=-1)
        li = []

        # compute search domain for today+ relativedelta(days=1)
        if max_ever:
            start_d = max_ever.name.date() + relativedelta(days=1)
            end_d = min_ever.name.date()
            count=0
            while min_ever.name.date() < start_d:
                end_d = start_d - relativedelta(days=1)
                tm = time(0, 0, 0)
                str_d = datetime.combine(start_d, tm)
                li += [('name', '<', str_d)]
                start_d = end_d
                str_d = datetime.combine(end_d, tm)
                li += [('name', '>', str_d)]

        the_sum = [[x, y] for x, y in zip(li[1:len(li):2], li[::2])]

        log_domain_li = []
        for i in range(len(the_sum)):
            log_domain_li.append(the_sum[i] + log_domain)

        return log_domain_li

    def convert_log_to_attendance(self):
        # self.env['hr.attendance'].search([('employee_id', '=', self.id)],limit=33).unlink()

        log_obj = self.env['biometric.log']
        attendance_obj = self.env['hr.attendance']
        lod_dom = self.compute_log_to_domain()

        for dom in lod_dom:
            # ('chek_in', '>', dom[0][2]), ('chek_in', '<', dom[1][2])
            # print(dom[0][2],'****',dom[1][2])
            self.env['hr.attendance'].search(
                [('employee_id', '=', self.id), ('check_in', '>', dom[0][2]), ('check_in', '<', dom[1][2])]).unlink()

            min_o = log_obj.search(dom, order='name asc', limit=1)
            max_o = log_obj.search(dom, order='name desc', limit=1)
            # prev_att = attendance_obj.search([('employee_id', '=', min_o.employee_id.id)], limit=1)
            if min_o and min_o == max_o:
               new_attendance = attendance_obj.create({
                    'employee_id': min_o.employee_id.id,
                    'check_in':min_o.name,
                    'check_out':max_o.name,
                    'state': 'fixout',

                })

            elif min_o and min_o != max_o:
                new_attendance = attendance_obj.create({
                        'employee_id': min_o.employee_id.id,
                        'check_in': min_o.name,
                        'check_out': max_o.name,
                        'state': 'right',
                    })
            else:
                continue