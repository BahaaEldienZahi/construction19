# -*- coding: utf-8 -*-
from odoo import models, fields, api


class HrLeaveType(models.Model):
    _inherit = "hr.leave.type"

    auto_allocation = fields.Boolean('Auto Allocation', default=False)
    auto_allocation_days = fields.Integer('Allocation Days')

    probation_period = fields.Boolean('Probation Period Allocation', default=False)
    probation_period_days = fields.Integer('Probation Days')

    defr_days = fields.Integer('Days', default=0, store=True, compute='_compute_defr_days')

    @api.depends('auto_allocation_days', 'probation_period_days')
    def _compute_defr_days(self):
        for rec in self:
            # if rec.auto_allocation==True:
            rec.defr_days = abs(rec.auto_allocation_days - rec.probation_period_days)
