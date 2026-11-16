# -*- coding: utf-8 -*-

from odoo import models, fields, api


class HrContract(models.Model):
    _inherit = "hr.contract"

    allowance_ids = fields.One2many('hr.contract.allowance', 'contract_id', string='Allowance')
    deduction_ids = fields.One2many('hr.contract.deduction', 'contract_id', string='Deduction')
    wage = fields.Monetary('Wage', required=True, tracking=True, help="Employee's monthly gross wage.",
                           group_operator="sum")
