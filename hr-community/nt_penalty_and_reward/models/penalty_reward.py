# -*- coding: utf-8 -*-
from odoo import models, fields, api


class PenaltyReward(models.Model):
    _name = "penalty.reward"
    _description = 'penalty and reward '

    employee_penalty_reward_id = fields.Many2one('employee.penalty.reward')
    pr_type = fields.Selection([('reward', 'Reward'),
                                ('penalty', 'Penalty')],
                               string="Type", default='reward')
    penalty_id = fields.Many2one('employee.penalty')
    reward_id = fields.Many2one('employee.reward')
    amount_day = fields.Float('Days')
    amount_money = fields.Float('Amount')
    amount_hour = fields.Float('Amount')
    payment_method = fields.Selection([('money', 'Money'),
                                       ('day', 'Days'),
                                       ('hour', 'Hours')
                                       ],
                                      string="Payment Method", default='money')
