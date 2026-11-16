from odoo import api, fields, models, tools


class EmployeeCategory(models.Model):
    _name = 'employee.category'
    _description = 'Category'

    name = fields.Char(string='Name')
    penalty_id = fields.Many2one('employee.penalty', readonly=0)
    subcategory_ids = fields.One2many(
        'employee.subcategory',
        'category_id',
        string='Sub Categories'
    )


class EmployeeCategoryLine(models.Model):
    _name = 'employee.category.line'
    _description = 'Employee Category Line'

    penalty_reward_id = fields.Many2one(
        'employee.penalty.reward',
        string='Penalty',
        ondelete='cascade'
    )
    category_id = fields.Many2one(
        'employee.category',
        string='Category',
        required=True
    )
    subcategory_id = fields.Many2one(
        'employee.subcategory',
        string='Sub Category',
        domain="[('category_id', '=', category_id)]"
    )
    amount_day = fields.Float('Days')

    @api.onchange('category_id')
    def _onchange_category_id(self):
        for rec in self:
            rec.subcategory_id = False
            rec.amount_day = 0.0

    @api.onchange('subcategory_id')
    def _onchange_subcategory_id(self):
        for rec in self:
            rec.amount_day = 0.0

            if not rec.subcategory_id:
                continue

            employee = rec.penalty_reward_id.employee_id
            occurrence = 1

            if employee:
                domain = [
                    ('subcategory_id', '=', rec.subcategory_id.id),
                    ('penalty_reward_id.employee_id', '=', employee.id),
                ]
                if rec._origin.id:
                    domain.append(('id', '!=', rec._origin.id))

                previous_count = self.env['employee.category.line'].search_count(domain)
                occurrence = previous_count + 1

            policy_line = self.env['policy.custom.line'].search([
                ('category_id', '=', rec.category_id.id),
                ('subcategory_id', '=', rec.subcategory_id.id),
            ], limit=1)

            if not policy_line:
                continue

            multiplier_map = {
                1: policy_line.first,
                2: policy_line.second,
                3: policy_line.third,
                4: policy_line.fourth,
            }
            multiplier = multiplier_map.get(occurrence, policy_line.fifth)

            rec.amount_day = rec.subcategory_id.amount_day * multiplier

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)

        for rec in records:
            self.env['penalty'].create({
                'employee_penalty_id': rec.penalty_reward_id.id,
                'penalty_id': rec.category_id.penalty_id.id,
                'amount_day': rec.amount_day,
                'payment_method': 'day',
            })

        return records


class EmployeeSubCategory(models.Model):
    _name = 'employee.subcategory'

    name = fields.Char(string='Name')
    category_id = fields.Many2one('employee.category', string='Parent Category')
    amount_day = fields.Float('Days')