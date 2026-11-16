# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    late_time_by_month = fields.Integer(
        string='Late Time By Month',
        related='company_id.late_time_by_month',
        readonly=False
    )
    penalty_days = fields.Float(
        string='Penalty Days',
        related='company_id.penalty_days',
        readonly=False
    )
    late_time_penalty_id = fields.Many2one(
        "employee.penalty",
        string='Late Time Penalty',
        related='company_id.late_time_penalty_id',
        readonly=False
    )
    late_time_reward_id = fields.Many2one(
        "employee.reward",
        string='Late Time Reward',
        related='company_id.late_time_reward_id',
        readonly=False
    )


class ResCompany(models.Model):
    _inherit = 'res.company'

    late_time_by_month = fields.Integer(string='Late Time By Month', default=0)
    penalty_days = fields.Float(string='Penalty Days', default=0)
    late_time_penalty_id = fields.Many2one("employee.penalty", string='Late Time Penalty')
    late_time_reward_id = fields.Many2one("employee.reward", string='Late Time Reward')
