import base64
import datetime
from datetime import datetime, date, time, timedelta

from lxml.builder import unicode
from odoo import models, fields, api, _, Command
from odoo.exceptions import UserError, ValidationError
import uuid


class HrJobOffer(models.Model):
    _name = 'hr.job.offer'
    _description = 'Job Offer'
    _inherit = ['mail.thread.cc', 'mail.activity.mixin']
    _rec_name = 'number'

    active = fields.Boolean(default=True)
    number = fields.Char(default='New', copy=False,tracking=True)
    employee_id = fields.Many2one('hr.employee',tracking=True)
    applicant_id = fields.Many2one('hr.applicant',tracking=True )
    department_id = fields.Many2one('hr.department', string='Department', related='applicant_id.department_id', store=True,tracking=True)
    user_id = fields.Many2one('res.users', compute='_compute_user_id', store=True, string='Manager',tracking=True)

    @api.depends('applicant_id', 'applicant_id.team_id', 'applicant_id.team_id.senior_id')
    def _compute_user_id(self):
        for rec in self:
            rec.user_id = False
            if rec.applicant_id.team_id and rec.applicant_id.team_id.senior_id:
                rec.user_id = rec.applicant_id.team_id.senior_id.id

    offer_date = fields.Date(default=fields.Date.context_today,tracking=True)
    company_id = fields.Many2one('res.company',tracking=True)
    reject_resason = fields.Text("Reject reason ",tracking=True)
    expire_date = fields.Date("Offer Expiration Date", default=lambda self: self._get_default_expire_date(),tracking=True)

    def _get_default_expire_date(self):
        # Start with today's date
        expire_date = date.today()
        working_days_added = 0

        # Add days until 5 working days are accounted for
        while working_days_added < 5:
            expire_date += timedelta(days=1)
            if expire_date.weekday() not in [4, 5]:  # 4 for Friday, 5 for Saturday
                working_days_added += 1

        return expire_date

    @api.constrains('offer_date', 'expire_date', 'availability_date')
    def _check_dates(self):
        for rec in self:
            if rec.expire_date and rec.offer_date and rec.expire_date < rec.offer_date:
                raise ValidationError(_("Offer Expiration Date cannot be earlier than Offer Date."))

            if rec.offer_date and rec.availability_date and rec.offer_date > rec.availability_date:
                raise ValidationError(_("Offer Date cannot be later than Availability Date."))

    def get_montly_default(self):
        if self.applicant_id:
            return self.applicant_id.salary_proposed
        else:
            return 0

    monthly_salary = fields.Float(tracking=True)
    prepaid_by = fields.Many2one('hr.employee',tracking=True)
    availability_date = fields.Date(tracking=True)
    days_before_availability = fields.Date(compute="_compute_7days_before_availability_date", store=True)
    state = fields.Selection([
        ('new', 'New'),
        ('req_hr_approve', 'Waiting HR Approve'),
        ('req_hr_approved', 'HR  Approved'),
        ('req_ceo_app', 'Waiting TL'),
        ('ceo_app', 'To Be Sent'),
        ('give_to_employee', 'Sent'),
        ('done', 'Accepted'),
        ('reject', 'Reject'),
        ('cancel', 'Cancelled'),
        ('expired', 'Expired'),
        ('employed', 'Done'),
    ], default='new',tracking=True)
    token = fields.Char(string='Token', copy=False)
    applicant_decision = fields.Selection([('accept', 'accept'), ('reject', 'reject')],tracking=True)
    expired = fields.Boolean('expired', default=False)
    reject_type = fields.Selection([('user', 'rejected by user '), ('applicant', 'rejected by Applicant')],tracking=True)
    reject_user = fields.Many2one('res.users', default=lambda self: self.env.user,tracking=True)
    reject_employee_reason = fields.Text('Reject reason',tracking=True)
    survey_access_token = fields.Text('')
    cancel_reason = fields.Many2one('cancel.offer.reason', string='Cancel Reason',tracking=True)

    @api.depends('availability_date')
    def _compute_7days_before_availability_date(self):
        for rec in self:
            if rec.availability_date:
                original_date = datetime.strptime(str(rec.availability_date), '%Y-%m-%d').date()
                rec.days_before_availability = original_date - timedelta(days=7)
                return rec.days_before_availability.strftime('%Y-%m-%d')

    def reactive_offer(self):
        for rec in self:
            rec.expired = False
            rec.state = 'give_to_employee'

    # open wizard reject reason
    def hr_reject(self):
        self.ensure_one()
        return {
            'name': _('Reject Reason'),
            'view_mode': 'form',
            'res_model': 'hr.job.reject.reason',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {'create': False,
                        'default_job_offer': self.id,
                        'active_test': False},
        }

    def team_lader_reject(self):
        self.ensure_one()
        return {
            'name': _('Reject Reason'),
            'view_mode': 'form',
            'res_model': 'hr.job.reject.reason',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {'create': False,
                        'default_job_offer': self.id,
                        'active_test': False},
        }

    def action_employed_applicant(self):
        for rec in self:
            rec.state = 'employed'

    def action_request_hr_approve(self):
        for rec in self:
            rec.state = 'req_hr_approve'

    def action_hr_approve(self):
        for rec in self:
            rec.state = 'req_ceo_app'

    def action_request_ceo_approve(self):
        for rec in self:
            rec.state = 'req_ceo_app'

    def action_ceo_approve(self):
        for rec in self:
            rec.state = 'ceo_app'

    # send email to applicant with job offer
    def action_give_to_employee(self):
        for rec in self:
            rec.state = 'give_to_employee'

            mail_template = self.env.ref('nt_recruitment_update.email_template_offer_link')
            mail_template.send_mail(self.id, force_send=True)
            rec.state = 'give_to_employee'

    def action_done(self):
        for rec in self:
            rec.state = 'done'

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancel'
            return {
                'type': 'ir.actions.act_window',
                'name': _('Cancel Job Offer'),
                'res_model': 'cancel.job.offer.wiz',
                'view_mode': 'form',
                'target': 'new',
                'context': {'current_id': self.id},
                'views': [[False, 'form']]
            }

    # in configration can set number of days before joing
    # date to send acceptence mail
    def _cron_send_acceptance_mail(self):
        done_offer_ids = self.env['hr.job.offer'].search(([('state', '=', 'done')]))
        acceptance_data = int(
            self.env['ir.config_parameter'].sudo().get_param('nt_recruitment_update.acceptance_mail'))
        today = fields.Date.today()

        for offer_id in done_offer_ids:
            availability_date = offer_id.applicant_id.availability
            date_to_send = availability_date - datetime.timedelta(days=acceptance_data)
            # datetime.date(2023, 6, 28)
            if today == date_to_send:
                offer_id.sudo().message_post_with_source('nt_recruitment_update.email_offer_acceptance', **{
                    'subtype_id': self.env['ir.model.data']._xmlid_to_res_id('mail.mt_note'),
                    'email_layout_xmlid': 'mail.mail_notification_light',
                })

    @api.model_create_multi
    def create(self, vals_list):
        for val in vals_list:
            res = super(HrJobOffer, self).create(val)
            if res.number == 'New':
                res.number = self.env['ir.sequence'].next_by_code('job.offer')
            res.token = str(uuid.uuid4())
            return res

    @api.ondelete(at_uninstall=False)
    def _unlink_if_no_cancel_or_ceo(self):
        for rec in self:
            if rec.state not in ['new']:
                raise UserError(_("You can't delete a job offer that canceled or approved from ceo."))

    #
    @api.model
    def _cron_archive_expired_job_offer(self):
        """cron job archive job offer after expiration date """
        expired_offers = self.env['hr.job.offer'].search([]).filtered(
            lambda r: r.expire_date and r.expire_date.day < datetime.now().day)
        if expired_offers:
            expired_offers.update({'expired': True,
                                   'state': 'expired'})

    def _cron_archive_rejected_job_offer_after7_days(self):
        """"for rejected job offer after 7 days """
        rejected_offers = self.env['hr.job.offer'].search([]).filtered(
            lambda r: r.state and r.state == 'reject')
        if rejected_offers:
            rejected_offers.update({'active': False})

    def _cron_send_servey_in_joining_date(self):
        """send survey to employee """
        survey_id = self.env['survey.survey'].search([('is_welcome_survey', '=', True)], limit=1)
        if survey_id:
            # mail_template = self.env.ref('nt_recruitment_update.email_template_survey_link')
            today = fields.Date.context_today(self)  # Get today's date based on user timezone
            new_emps_today = self.env['hr.job.offer'].search([]).filtered(

                lambda r: r.availability_date and r.availability_date == today)
            for emp in new_emps_today:
                mail_template = self.env.ref('nt_recruitment_update.email_template_survey_link')
                emp.survey_access_token = survey_id.access_token
                mail_template.send_mail(emp.id, force_send=True)

    @api.model
    def _cron_create_tickets_7days_before_joining_date(self):
        """create ticket according to boarding stages in recruitment"""
        self.env.registry.clear_cache()
        help_desk_ticket_id = self.env['helpdesk.ticket']
        boarding_stage_id = self.env['boarding.stage'].search([])
        today = date.today()
        today_date = fields.Date.from_string(today)
        new_emps_10days_before = self.env['hr.job.offer'].search([('state', '=', 'done')]).filtered(
            lambda r: r.days_before_availability and r.days_before_availability == today_date)
        for emp in new_emps_10days_before:
            for stage in boarding_stage_id:
                help_desk_ticket_id.create({
                    'app_id': emp.applicant_id.id,
                    'name': stage.description if stage.description else 'new',
                    'team_id': stage.help_desk_team.id,
                    'category_id': stage.category.id,
                    'priority': '1',
                    'ticket_type_id': stage.ticket_type_id.id,
                    'user_id': stage.user_id.id,
                    'employee_id': stage.responsible_id.id,
                    'description_html': ' Employee Name: ' + unicode(emp.applicant_id.name) +
                                        '<br>' + ' Job Title: ' + unicode(emp.applicant_id.job_id.name)
                                        + '<br>' + 'Department: ' + unicode(emp.applicant_id.department_id.name) +
                                        '<br>' + 'Work Email: ' + unicode(emp.applicant_id.work_email) +
                                        '<br>' + 'Joining Date: ' + unicode(emp.applicant_id.availability),
                })

    def send_welcome_mail(self):
        self.ensure_one()
        survey_id = self.env['survey.survey'].search([('is_welcome_survey', '=', True)], limit=1)
        if survey_id:
            mail_template = self.env.ref('nt_recruitment_update.email_template_survey_link')
            mail_template.with_context(survey_token=survey_id.access_token)
            mail_template.send_mail(self.id, force_send=True)

    # button hr can review job offer before send
    def action_review_offer(self):
        if self.token:
            # Construct the URL
            url = f"/recruitment/offer/{self.token}"

            # Return an action for the URL
            return {
                'type': 'ir.actions.act_url',
                'url': url,
                'target': 'current',  # or 'self' to open in the same window
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'hr.job.offer',
                'view_mode': 'form',
                'res_id': self.id,
                'target': 'new',  # or 'self' to open in the same window
            }
