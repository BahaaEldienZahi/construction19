# -*- coding: utf-8 -*-

from odoo import models, fields, api


class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    # @api.model_create_multi
    # def create(self, vals):
    #     res = super(HrApplicant, self).create(vals)
    #     requests = self.env['hiring.request'].search(
    #         [('job_position_id', '=', res.job_id.id), ('status', '=', 'in_progress')], order='create_date asc', limit=1)
    #     for req in requests:
    #         req.no_of_applications += 1
    #     return res

    @api.constrains('stage_id')
    def _onchange_hired_number_in_hiring_requests(self):
        for rec in self:
            first_stage = self.env['hr.recruitment.stage'].search([], order='id asc', limit=1)
            for stage in first_stage:
                if rec.stage_id != stage:
                    hiring_requests = self.env['hiring.request'].search(
                        [('job_position_id', '=', rec.job_id.id), ('status', '=', 'in_progress')],
                        order='create_date asc',
                        limit=1)
                    for hire_req in hiring_requests:
                        if hire_req.job_application_id:
                            if rec.id not in hire_req.job_application_id.ids:
                                hire_req.job_application_id = [(4, rec.id)]
                                hire_req.no_of_applications += 1
                        else:
                            hire_req.job_application_id = [(4, rec.id)]
                            hire_req.no_of_applications += 1
                # hired_no = 0
                if rec.stage_id.hired_stage:
                    requests = self.env['hiring.request'].search(
                        [('job_position_id', '=', rec.job_id.id), ('status', '=', 'in_progress')],
                        order='create_date asc',
                        limit=1)
                    for req in requests:
                        req.hired += 1
                        if req.number_of_vacancies == req.hired:
                            req.status = 'done'
                            hiring_requests_obj = self.env['hiring.request'].search(
                                [('job_position_id', '=', req.job_position_id.id), ('status', '=', 'in_progress')],
                                order='create_date asc',
                                limit=1)
                            if not hiring_requests_obj:
                                req.job_position_id.is_published = req.job_position_id.website_published = False
                                req.job_position_id.no_of_recruitment = 0
