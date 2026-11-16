from odoo import api, fields, models


class HiringRequest(models.Model):
    _inherit = 'hiring.request'

    planned_count = fields.Integer(string="Planned", readonly=True)
    current_employees = fields.Integer(string="Current Employees", readonly=True)
    duration = fields.Integer(
        string="Duration (Days)",
        compute="_compute_duration",
        store=True,
    )
    deviation = fields.Integer(
        string="Diff",
        compute='_compute_deviation',
        store=True,
    )

    @api.depends('request_date', 'closed_date')
    def _compute_duration(self):
        for rec in self:
            if rec.request_date and rec.closed_date:
                rec.duration = (rec.closed_date - rec.request_date).days
            else:
                rec.duration = 0

    @api.depends('current_employees', 'job_position_id.planning_ids.number_of_recruitment')
    def _compute_deviation(self):
        for rec in self:
            actual = rec.current_employees or 0
            if rec.job_position_id and rec.job_position_id.planning_ids:
                last_planning = rec.job_position_id.planning_ids.sorted('id')[-1]
                planned = last_planning.number_of_recruitment or 0
            else:
                planned = 0
            rec.deviation = abs(actual - planned)

    def action_submit(self):
        """Override to populate planned_count and current_employees before submitting."""
        for rec in self:
            if rec.job_position_id and rec.job_position_id.planning_ids:
                last_planning = rec.job_position_id.planning_ids[-1]
                rec.planned_count = last_planning.number_of_recruitment

            if rec.department_id:
                rec.current_employees = self.env['hr.employee'].search_count([
                    ('department_id', '=', rec.department_id.id),
                    ('active', '=', True),
                ])
        return super().action_submit()

    def action_done(self):
        for rec in self:
            rec.status = 'done'
            rec.closed_date = fields.Date.today()
            rec.job_position_id.is_published = False
            rec.job_position_id.website_published = False
