# -*- coding: utf-8 -*-
from odoo import models, fields, api


class Penalty(models.Model):
    _name = "penalty"
    _description = 'penalties'

    employee_penalty_id = fields.Many2one('employee.penalty.reward')
    pr_type = fields.Selection([('penalty', 'Penalty')], string="Type", default='penalty')

    penalty_id = fields.Many2one('employee.penalty')
    amount_day = fields.Float('Days')
    amount_hour = fields.Float('Hours')
    amount_money = fields.Float('Amount')
    payment_method = fields.Selection([('money', 'Money'),
                                       ('day', 'Days'),
                                       ('hour', 'Hours')],
                                      string="Payment Method", default='money')


