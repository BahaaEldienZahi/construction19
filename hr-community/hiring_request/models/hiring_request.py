# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class HiringRequest(models.Model):
    _name = 'hiring.request'
    _inherit = ['mail.thread.cc', 'mail.activity.mixin']
    _description = 'Hiring Requests Cycle'
    _rec_name = 'name'

    _sql_constraints = [
        ('name_uniq', 'unique (name)', """Only one value can be defined for each given usage!"""),
    ]

    name = fields.Char(string='Code', readonly=True, default='New', copy=False)
    job_position_id = fields.Many2one('hr.job', string='Job Position', required=True)
    department_id = fields.Many2one('hr.department', string='Department', related='job_position_id.department_id',store=True)
    expected_salary_from = fields.Float(string='Expected Salary')
    expected_salary_to = fields.Float()
    number_of_vacancies = fields.Integer(string='Target', required=True, default=1)
    hired = fields.Integer(string='Hired', readonly=True)
    no_of_applications = fields.Integer(string='No. of applications', readonly=True)
    requested_by = fields.Many2one('res.users', string='Requested by', default=lambda self: self.env.user,
                                   readonly=True)
    request_date = fields.Date(string='Request Date')
    closed_date = fields.Date(string='Closed Date')
    # user_id = fields.Many2one('res.user', default=lambda self: self.env.user)
    rejection_reason = fields.Text(string='Rejection Reason', readonly=True)
    is_visible_button = fields.Boolean(string='Check Rejection', default=False, compute='_compute_rejection')
    is_readonly_fields = fields.Boolean(string='Check Readonly', default=False, )
    job_application_id = fields.Many2many('hr.applicant', string='Applications')
    no_of_experience_from = fields.Float('Years of Experience', digits=(12, 1))
    no_of_experience_to = fields.Float(digits=(12, 1))
    status = fields.Selection(
        [('draft', 'Draft'),
         ('manager_approve', 'Manager Approval'),
         ('hr_approve', 'Hr Approval'),
         ('ceo_approve', 'CEO Approval'),
         ('in_progress', 'In Progress'),
         ('done', 'Done'),
         ('reject', 'Rejected'), ], ondelete={'manager_approve': 'cascade', 'reject': 'cascade', }, string='Stage',
        readonly=True, default='draft', tracking=True, copy=False)
    active = fields.Boolean(string='Active', default=True, )
    company_id = fields.Many2one('res.company')


    @api.model_create_multi
    def create(self, vals):
        """
            Override create method
             - sequence name
        """
        for val in vals:
            if val.get('name', 'New') == 'New':
                val['name'] = self.env['ir.sequence'].next_by_code(
                    'hiring.request') or '/'
            return super(HiringRequest, self).create(val)

    @api.onchange('expected_salary_from', 'expected_salary_to')
    def _onchange_expected_salary(self):
        for rec in self:
            if rec.expected_salary_from and rec.expected_salary_to:
                if rec.expected_salary_from > rec.expected_salary_to:
                    raise ValidationError(_('The expected salary from is greater than the expected salary to.'))

    @api.depends('status', 'requested_by')
    def _compute_rejection(self):
        for rec in self:
            rec.is_visible_button = False
            rec.is_readonly_fields = True

            if rec.user_has_groups('hiring_request.hiring_request_manager_group') and rec.status == 'manager_approve':
                rec.is_visible_button = True
                rec.is_readonly_fields = False
            elif rec.user_has_groups('hiring_request.hiring_request_hr_group') and rec.status == 'hr_approve':
                rec.is_visible_button = True
                rec.is_readonly_fields = True
            elif rec.user_has_groups('hiring_request.hiring_request_ceo_group') and rec.status == 'ceo_approve':
                rec.is_visible_button = True
                rec.is_readonly_fields = False
            else:
                rec.is_visible_button = False
                if rec.user_has_groups('hiring_request.hiring_request_user_group') and rec.status == 'draft':
                    rec.is_readonly_fields = False
                else:
                    rec.is_readonly_fields = True

    @api.constrains('name')
    def _onchange_name(self):
        for rec in self:
            rec.request_date = rec.create_date.date()

    def action_submit(self):
        for rec in self:
            # print(rec.no_of_experience_from)
            # if rec.no_of_experience_from == 0 or rec.no_of_experience_to == 0:
            #     print("VALIDATION")
            #     raise ValidationError(_('Years of Experience must be Greater Than 0.'))
            if rec.job_position_id.department_id:
                if rec.job_position_id.department_id.manager_approve:
                    rec.status = 'manager_approve'
                else:
                    rec.status = 'hr_approve'
            else:
                rec.status = 'hr_approve'

    def action_manager_approve(self):
        for rec in self:
            rec.status = 'hr_approve'

    def action_hr_approve(self):
        for rec in self:
            rec.status = 'ceo_approve'
    def action_ceo_approve(self):
        for rec in self:
            rec.status = 'in_progress'
            rec.closed_date = fields.Date.today()

            # # send email to HR to confirm that hiring requested is created
            # mail_template = self.env.ref('hiring_request.email_template_hiring_request_created')
            # mail_template.send_mail(self.id, force_send=True)

            rec.job_position_id.is_published = rec.job_position_id.website_published = True
            rec.job_position_id.no_of_recruitment += rec.number_of_vacancies

            groups = self.env['res.groups'].search(
                [('id', '=', self.env.ref('hiring_request.hiring_request_hr_group').id)])
            users = False
            user_partners = []
            for group in groups:
                users = group.users
            for user in users:
                user_partners.append(user.partner_id.id)

            notification = {'subject': "CEO has been approved a hiring request.",
                            'body': _("CEO has ben approved the hiring request number: %s", str(rec.name)),
                            'partner_ids': user_partners, 'author_id': rec.requested_by.partner_id.id, }
            thread_pool = self.pool.get('mail.thread')
            thread_pool.message_post(self, message_type="notification", **notification)

    def action_reject(self):
        return {
            'name': 'Rejection Reason',
            'type': 'ir.actions.act_window',
            'res_model': 'hiring.rejection.reason.wizard',
            'view_mode': 'form',
            'target': 'new',
        }
