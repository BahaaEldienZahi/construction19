from odoo import api, fields, models


class EmployeePenaltyReward(models.Model):
    _inherit = 'employee.penalty.reward'

    employee_category_ids = fields.One2many(
        'employee.category.line',
        'penalty_reward_id',
        string='Categories'
    )