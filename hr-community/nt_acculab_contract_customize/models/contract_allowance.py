# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ContractAllowance(models.Model):
    _name = "contract.allowance"

    name = fields.Char(string='Allowance')


class ContractDeduction(models.Model):
    _name = "contract.deduction"

    name = fields.Char(string='Deduction')
