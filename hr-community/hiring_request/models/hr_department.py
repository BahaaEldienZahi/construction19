# -*- coding: utf-8 -*-

from odoo import models, fields, api


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    manager_approve = fields.Boolean(string='VP Approval', default=False)

