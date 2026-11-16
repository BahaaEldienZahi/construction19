
from odoo import _, api, fields, models



class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    user_id = fields.Many2many(
        'res.users',
        'hr_applicant_user_rel',
        'applicant_id',
        'user_id',
        string='Recruiters'
    )
    technical_interviewer_ids = fields.Many2many(
        'hr.employee',
        'hr_applicant_technical_interviewer_rel',
        'applicant_id',
        'employee_id',
        string='Technical Interviewers'
    )


