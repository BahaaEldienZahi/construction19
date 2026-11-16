from odoo import api, fields, models


class RecruitmentPlanning(models.Model):
    _name = 'recruitment.planned'
    _description = 'Recruitment Planned'

    job_id = fields.Many2one('hr.job', string="Job Position", ondelete='cascade')
    date_from = fields.Date(string="From Date")
    number_of_recruitment = fields.Integer(string="Number", default=0)
