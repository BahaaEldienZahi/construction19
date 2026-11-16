""" Initialize Stage Move """

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from odoo import Command

class StageMove(models.TransientModel):
    _name = 'stage.move'
    _description = 'Stage Move'

    feedback = fields.Text()
    hr_applicant_id = fields.Many2one('hr.applicant')
    stage_id = fields.Many2one('hr.recruitment.stage', string='New Stage', required=True,
                               domain="[('id', '!=',current_stage_id )]")
    current_stage_id = fields.Many2one('hr.recruitment.stage')
    feedback_required = fields.Boolean(related='current_stage_id.feedback_required')

    user_id = fields.Many2one('res.users', 'Assigned to', default=lambda self: self.env.user, )
    required_activity = fields.Boolean(related='stage_id.required_activity')
    interview_details_required = fields.Boolean(related='stage_id.interview_details_required')
    interview_details_required2 = fields.Boolean(related='current_stage_id.interview_details_required')
    meeting_type = fields.Selection([
        ('online', 'Online'),
        ('offline', 'Offline'),
    ], string='Meeting Type')
    meeting_link = fields.Char(string='Meeting Link')
    meeting_note = fields.Char()
    interview_date = fields.Datetime(string='Interview Date')

    @api.onchange('stage_id')
    def _onchange_stage_id(self):
        """ stage_id """
        if self.stage_id:
            if self.user_has_groups(
                    'nt_recruitment_update.group_team_leader') and not self.stage_id.allow_team_leader:
                raise ValidationError(
                    _('You are not allowed to move at this stage'))
            elif self.user_has_groups(
                    'nt_recruitment_update.group_interviewer') and not self.stage_id.allow_recruiter:
                raise ValidationError(
                    _('You are not allowed to move at this stage'))
            # elif self.user_has_groups(
            #         'nt_recruitment_update.group_interviewer') and not self.stage_id.allow_interviewer:
            #     raise ValidationError(
            #         _('You are not allowed to move at this stage'))

    def stage_move(self):
        if self.feedback_required:
            self.hr_applicant_id.write(
                {
                    'feedback_applicant_ids': [Command.create({'feedback': self.feedback, 'stage_id': self.current_stage_id.id})],
                    'stage_id': self.stage_id.id,
                    'meeting_type': self.meeting_type,
                    'meeting_link': self.meeting_link,
                    'meeting_note': self.meeting_note,
                    'interview_date': self.interview_date,
                }
            )
        else:
            self.hr_applicant_id.write(
                {
                    'stage_id': self.stage_id.id,
                    'meeting_type': self.meeting_type,
                    'meeting_link': self.meeting_link,
                    'meeting_note': self.meeting_note,
                    'interview_date': self.interview_date,
                }
            )
        self.hr_applicant_id._check_stage()

        # if self.required_activity:
        #     self.env['mail.activity'].create(
        #         {'res_id': self.hr_applicant_id.id,
        #          'res_model': 'hr.applicant',
        #          'res_model_id': self.env['ir.model'].search(
        #              [('model', '=', self.hr_applicant_id._name)]).id,
        #          'activity_type_id': self.stage_id.activity_type_id.id,
        #          'summary': 'An Activity Created for this Application',
        #          'date_deadline': fields.Date().today() + relativedelta(days=5),
        #          'user_id': self.env.uid})

        return {'type': 'ir.actions.client', 'tag': 'reload'}
