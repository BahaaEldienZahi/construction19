from odoo import fields, models, api, _

class HrContract(models.Model):
    _inherit = 'hr.contract'

    monthly_additions = fields.Float(
        string='إجمالي الإضافات الشهرية',
        default=0.0,
        help='مجموع المكافآت والأيام التعويضية والبدلات المتغيرة هذا الشهر'
    )
    profits = fields.Float('أرباح')
    vacation_allowance = fields.Float('بدل اجازات')
    insurance_salary = fields.Float(
        string='الأجر التأميني',
        default=0.0,
        help='الأجر الذي يتم احتساب التأمينات الاجتماعية على أساسه'
    )

    donot_tax_bracket = fields.Boolean('Do Not Apply Tax Bracket', default=False)

    second_tax_bracket = fields.Float(compute='_compute_tax_bracket', store=True)
    third_tax_bracket  = fields.Float(compute='_compute_tax_bracket', store=True)
    fourth_tax_bracket = fields.Float(compute='_compute_tax_bracket', store=True)
    fiveth_tax_bracket = fields.Float(compute='_compute_tax_bracket', store=True)
    sixth_tax_bracket  = fields.Float(compute='_compute_tax_bracket', store=True)
    seven_tax_bracket = fields.Float(compute='_compute_tax_bracket', store=True)

    second_checked = fields.Boolean('Is Check', compute='_compute_tax_bracket', store=True)
    third_checked  = fields.Boolean('Is Check', compute='_compute_tax_bracket', store=True)
    fourth_checked = fields.Boolean('Is Check', compute='_compute_tax_bracket', store=True)
    fiveth_checked = fields.Boolean('Is Check', compute='_compute_tax_bracket', store=True)
    sixth_checked  = fields.Boolean('Is Check', compute='_compute_tax_bracket', store=True)
    seven_checked = fields.Boolean('Is Check',compute='_compute_tax_bracket', store=True)

    @api.depends('wage','medical_allowance','monthly_additions','donot_tax_bracket')
    def _compute_tax_bracket(self):

        for contract in self:
            if contract.donot_tax_bracket:
                contract.second_tax_bracket = 0
                contract.third_tax_bracket = 0
                contract.fourth_tax_bracket = 0
                contract.fiveth_tax_bracket = 0
                contract.sixth_tax_bracket = 0
                contract.seven_tax_bracket = 0

                contract.second_checked = False
                contract.third_checked = False
                contract.fourth_checked = False
                contract.fiveth_checked = False
                contract.sixth_checked = False
                contract.seven_checked = False
                continue
            else:
                wage = (contract.wage or 0.0) + (contract.monthly_additions or 0.0)
                social_insurance = 1837 if contract.wage  > 16700 else contract.wage * 0.11
                medical = min(833.33, contract.medical_allowance)
                net_monthly_wage = wage - social_insurance - medical
                annual_wage = (net_monthly_wage * 12) - 20000

                # Reset all fields
                contract.second_tax_bracket = 0
                contract.third_tax_bracket = 0
                contract.fourth_tax_bracket = 0
                contract.fiveth_tax_bracket = 0
                contract.sixth_tax_bracket = 0
                contract.seven_tax_bracket = 0

                contract.second_checked = False
                contract.third_checked = False
                contract.fourth_checked = False
                contract.fiveth_checked = False
                contract.sixth_checked = False
                contract.seven_checked = False

                second_bracket_start = 55000 if annual_wage > 600000 else 40000

                if annual_wage <= second_bracket_start:
                    pass
                elif annual_wage <= 55000:
                    contract.second_tax_bracket = 55000 if annual_wage > 600000 else 15000
                    contract.second_checked = True
                elif annual_wage <= 70000:
                    contract.second_tax_bracket = 55000 if annual_wage > 600000 else 15000
                    contract.third_tax_bracket = annual_wage - 55000
                    contract.second_checked = True
                    contract.third_checked = True
                elif annual_wage <= 200000:
                    contract.second_tax_bracket = 55000 if annual_wage > 600000 else 15000
                    contract.third_tax_bracket = 15000
                    contract.fourth_tax_bracket = annual_wage - 70000
                    contract.second_checked = True
                    contract.third_checked = True
                    contract.fourth_checked = True
                elif annual_wage <= 400000:
                    contract.second_tax_bracket = 55000 if annual_wage > 600000 else 15000
                    contract.third_tax_bracket = 15000
                    contract.fourth_tax_bracket = 130000
                    contract.fiveth_tax_bracket = annual_wage - 200000
                    contract.second_checked = True
                    contract.third_checked = True
                    contract.fourth_checked = True
                    contract.fiveth_checked = True
                elif annual_wage <= 1200000:
                    contract.second_tax_bracket = 55000 if annual_wage > 600000 else 15000
                    contract.third_tax_bracket = 15000
                    contract.fourth_tax_bracket = 130000
                    contract.fiveth_tax_bracket = 200000
                    contract.sixth_tax_bracket = annual_wage - 400000
                    contract.second_checked = True
                    contract.third_checked = True
                    contract.fourth_checked = True
                    contract.fiveth_checked = True
                    contract.sixth_checked = True
                else:
                    contract.second_tax_bracket = 55000 if annual_wage > 600000 else 15000
                    contract.third_tax_bracket = 15000
                    contract.fourth_tax_bracket = 130000
                    contract.fiveth_tax_bracket = 200000
                    contract.sixth_tax_bracket = 800000
                    contract.seven_tax_bracket = annual_wage - 1200000
                    contract.second_checked = True
                    contract.third_checked = True
                    contract.fourth_checked = True
                    contract.fiveth_checked = True
                    contract.sixth_checked = True
                    contract.seven_checked = True