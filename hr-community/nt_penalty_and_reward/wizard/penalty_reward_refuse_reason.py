from odoo import fields, models


class PenaltyRewardRefuseReason(models.TransientModel):
    _name = "penalty.reward.refuse.reason"

    penalty_reward_refuse_reason = fields.Text(string="Refuse Reason", required=True)

    def refuse_reason(self):
        if self.env.context.get('active_model') == 'employee.penalty.reward':
            active_model_id = self.env.context.get('active_id')
            hr_obj = self.env['employee.penalty.reward'].search([('id', '=', active_model_id)])
            if hr_obj:
                print('yes')
                hr_obj.write({
                    'penalty_reward_refuse_reason': self.penalty_reward_refuse_reason,
                    'state': 'rej'
                })
