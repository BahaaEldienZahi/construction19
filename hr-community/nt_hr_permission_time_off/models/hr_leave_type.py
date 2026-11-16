# -*- coding: utf-8 -*-

from odoo import models, fields, api


class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    is_permission = fields.Boolean('Is a permission')
    permission_hours = fields.Integer('Permission hours')
    visibility = fields.Boolean()
    leave_type_ids = fields.Many2many(
        'hr.leave.type', 'leave_type_rel', 'type_id', 'type_leave_id',
        domain="[('id', '!=', id)]"
    )
    all_days = fields.Boolean()
    required_attachment = fields.Boolean()
    mission = fields.Boolean()


