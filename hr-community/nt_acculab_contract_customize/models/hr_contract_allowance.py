# -*- coding: utf-8 -*-

from odoo import models, fields, api


class HrContractAllowance(models.Model):
    _name = "hr.contract.allowance"

    allowance_id = fields.Many2one('contract.allowance', string='Allowance')
    contract_id = fields.Many2one('hr.contract', string='Contract')
    amount = fields.Float(string='amount')


class HrContractDeduction(models.Model):
    _name = "hr.contract.deduction"

    deduction_id = fields.Many2one('contract.deduction', string='Deduction')
    contract_id = fields.Many2one('hr.contract', string='Contract')

    amount = fields.Float(string='amount')
