from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    attendance_policy_id = fields.Many2one(comodel_name='hr.attendance.policy', string='Attendance Policy', )

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        attendance_policy_id = params.get_param('rm_hr_attendance_sheet.attendance_policy_id',)

        if attendance_policy_id:
            res.update(
                attendance_policy_id=int(attendance_policy_id),
            )
        return res

    def set_values(self):
        res = super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('rm_hr_attendance_sheet.attendance_policy_id',
                                                         self.attendance_policy_id.id)
        return res
