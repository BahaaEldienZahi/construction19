from odoo import models, fields


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    penalty_reward_dep_id = fields.Many2one('penalty.reward.batch')
