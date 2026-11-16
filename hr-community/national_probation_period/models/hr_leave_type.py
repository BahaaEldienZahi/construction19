# -*- coding: utf-8 -*-
from odoo import models, fields, api


class HrLeaveType(models.Model):
    _inherit = "hr.leave.type"

    _sql_constraints = [
        ('uniqueness_probation_period_type', 'UNIQUE(probation_period)',
         'An Probation Period Time off type cannot be more than One'),
    ]

    auto_allocation = fields.Boolean('Auto Allocation', default=False)
    auto_allocation_days = fields.Integer('Auto Days')

    probation_period = fields.Boolean('Probation Period Allocation', default=False)
    probation_period_days = fields.Integer('Probation Days')
