from odoo import models, fields, api


class ReferralBonus(models.Model):
    _name = 'referral.bonus'
    _description = 'Referral Bonus'

    name = fields.Char(string="Name", required=False, )
    amount = fields.Integer(string="Amount",  required=False, )