from odoo import fields, models, api, _


class HrOvertime(models.Model):
    _inherit = 'hr.overtime'

    overtime_att = fields.Float(
        string='Overtime Attendance',
        compute='_compute_overtime_att',
        store=True
    )

    @api.depends('employee_id', 'date_from', 'date_to')
    def _compute_overtime_att(self):
        for rec in self:
            rec.overtime_att = 0.0

            if not rec.employee_id or not rec.date_from or not rec.date_to:
                continue

            attendances = self.env['hr.attendance'].search([
                ('employee_id', '=', rec.employee_id.id),
                ('check_in', '<', rec.date_to),
                ('check_out', '>', rec.date_from),
            ])

            calendar = rec.employee_id.resource_calendar_id

            for line in calendar.attendance_ids:
                print(
                    line.dayofweek,
                    line.hour_from,
                    line.hour_to,
                )

            total_overtime = 0.0

            calendar = rec.employee_id.resource_calendar_id

            for att in attendances:
                if not att.check_out:
                    continue

                overlap_start = max(att.check_in, rec.date_from)
                overlap_end = min(att.check_out, rec.date_to)


                if overlap_end <= overlap_start:
                    continue

                worked_hours = (overlap_end - overlap_start).total_seconds() / 3600.0

                planned_hours = calendar.get_work_hours_count(
                    overlap_start,
                    overlap_end,
                    compute_leaves=False,
                )

                overtime = max(worked_hours - planned_hours, 0.0)



                total_overtime += overtime

            rec.overtime_att = total_overtime


    def action_submit_to_finance(self):
        for rec in self:
            final_hours = int(min(rec.days_no_tmp or 0.0, rec.overtime_att or 0.0))

            rec.write({
                'days_no_tmp': final_hours,
                'days_no': final_hours,
            })

        return super(HrOvertime, self).action_submit_to_finance()
