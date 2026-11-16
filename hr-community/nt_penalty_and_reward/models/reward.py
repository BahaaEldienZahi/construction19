# -*- coding: utf-8 -*-
from odoo import models, fields, api


class Reward(models.Model):
    _name = "reward"
    _description = 'rewards'

    employee_reward_id = fields.Many2one('employee.penalty.reward')
    pr_type = fields.Selection([('reward', 'Reward')], string="Type", default='reward')
    reward_id = fields.Many2one('employee.reward')
    amount_day = fields.Float('Days')
    amount_money = fields.Float('Amount')
    amount_hour = fields.Float('Hours')
    payment_method = fields.Selection([('money', 'Money'),
                                       ('hour', 'Hours'),
                                       ('day', 'Days')],
                                      string="Payment Method", default='money')
