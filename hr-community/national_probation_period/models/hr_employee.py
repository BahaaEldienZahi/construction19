from odoo import models, fields, api
from dateutil.relativedelta import relativedelta
from datetime import datetime


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    in_probation_period = fields.Boolean('IN Probation Period', default=False)

    date_start = fields.Date(related='contract_id.date_start', store=True, readonly=False, required=True)
    date_end = fields.Date(related='contract_id.probation_date_end', readonly=False)
    is_insurance_for_children = fields.Boolean()
    is_insurance_for_wife = fields.Boolean()
    probation_period_end_date = fields.Date()
    today_date = fields.Date("Today's date", default=fields.Date.today())
    contract_end_date = fields.Date("End Date")
    remain_probation_period = fields.Integer(compute="_compute_remain_probation_period", )

    # @api.depends('date_start', 'probation_period_end_date')
    def _compute_remain_probation_period(self):
        for record in self:
            record.remain_probation_period = 0
            if record.probation_period_end_date:
                if record.probation_period_end_date > fields.Date.today():
                    probation_date_end = record.probation_period_end_date
                    date_start = record.date_start
                    if date_start and probation_date_end:
                        date_deffer = (probation_date_end - fields.Date.today()).days

                        record.remain_probation_period = int(date_deffer)

    @api.model_create_multi
    def create(self, vals):
        for val in vals:
            val['in_probation_period'] = True
        res_super = super(HrEmployee, self).create(vals)
        for res in res_super:
            if res.in_probation_period:
                probation_obj = self.env['employee.probation.period'].sudo().create({'employee_id': res.id})
                hr_timeoff_type_objs = self.env['hr.leave.type'].search([('probation_period', '=', True)], limit=1)
                if hr_timeoff_type_objs:
                    time_allocation_obj = self.env['hr.leave.allocation'].search(
                        [('holiday_status_id', '=', hr_timeoff_type_objs.id),
                         ('employee_id', '=', res.id)], limit=1)
                    if not time_allocation_obj:
                        allocation_object = {
                            'name': 'Probation Period of ' + res.name,
                            'employee_id': res.id,
                            'holiday_status_id': hr_timeoff_type_objs.id,
                            'number_of_days': hr_timeoff_type_objs.probation_period_days,
                        }
                        time_allocation = self.env['hr.leave.allocation'].sudo().create(allocation_object)
                        time_allocation.action_validate()
        return res_super
