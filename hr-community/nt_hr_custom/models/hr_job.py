from odoo import api, fields, models


class HrJob(models.Model):
    _inherit = 'hr.job'

    planning_ids = fields.One2many(
        'recruitment.planned', 'job_id', string="Planned",
    )
    planned_count = fields.Integer(
        string="Planned",
        compute='_compute_hiring_stats',
        store=True,
    )
    actual_count = fields.Integer(
        string="Actual",
        compute='_compute_hiring_stats',
        store=True,
    )
    deviation = fields.Integer(
        string="Deviation",
        compute='_compute_hiring_stats',
        store=True,
    )



    @api.depends('planning_ids.number_of_recruitment', 'no_of_hired_employee')
    def _compute_hiring_stats(self):
        for rec in self:
            rec.planned_count = sum(rec.planning_ids.mapped('number_of_recruitment'))
            rec.actual_count = rec.no_of_hired_employee or 0
            rec.deviation = rec.actual_count - rec.planned_count
