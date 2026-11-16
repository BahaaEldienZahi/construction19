from odoo import api, fields, models


class HrContract(models.Model):
    _inherit = 'hr.contract'

    can_edit_state = fields.Boolean(
        compute="_compute_can_edit_state",
        store=False,
    )

    @api.depends('state')
    @api.depends_context('uid')
    def _compute_can_edit_state(self):
        is_manager = self.env.user.has_group(
            'nt_hr_custom.group_nt_hr_custom_contract_manager'
        )
        for rec in self:
            rec.can_edit_state = is_manager
