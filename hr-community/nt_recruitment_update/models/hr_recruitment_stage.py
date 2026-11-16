from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class HrRecruitmentStage(models.Model):
    _inherit = 'hr.recruitment.stage'

    interview_details_required = fields.Boolean(string='Interview Details Required')
    allow_team_leader = fields.Boolean(string='Allow To Team Leader')
    feedback_required = fields.Boolean()
    required_activity = fields.Boolean()
    job_offer = fields.Boolean()
    activity_type_id = fields.Many2one('mail.activity.type', string='Activity Type')
    allow_recruiter = fields.Boolean(string='Allow To Recruiter')
    show_send_reminder = fields.Boolean(string='Show send Attachment Reminder')
    allow_interviewer= fields.Boolean(string ='Allow To Interviewer ')


class RecruitmentTeam(models.Model):
    _name = 'recruitment.team'
    _description = 'Recruitment Team'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _check_company_auto = True

    name = fields.Char(
        required=True,
        translate=True,
    )
    active = fields.Boolean(
        default=True
    )
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
    )
    senior_id = fields.Many2one(
        'res.users', string='Team leader',
        domain=lambda self: [('share', '=', False),
                             ('groups_id', '=', self.env.ref(
                                 'nt_recruitment_update.group_team_leader').id)]
    )
    team_leader_ids = fields.Many2many(
        'res.users', domain=lambda self: [('share', '=', False),
                                          ('groups_id', '=', self.env.ref(
                                              'nt_recruitment_update.group_interviewer').id)],
        string='Interviewer'
    )


