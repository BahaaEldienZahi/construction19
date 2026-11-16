# -*- coding: utf-8 -*-
import cProfile
import pstats
import io
import logging
_logger = logging.getLogger(__name__)
from dateutil.relativedelta import relativedelta
from datetime import datetime, time, timedelta, date
from odoo import _, api, fields, models, Command
from odoo.exceptions import UserError, ValidationError
import pytz


class HrApplicant(models.Model):
    _inherit = 'hr.applicant'
    _order = "interview_date asc"

    @api.model
    def _default_ref_employee_id(self):
        ref_employee_id = self.emp_id.id
        if self.env.user.has_group('referral_custom.group_referral_hr_user'):
            return ref_employee_id
        else:
            return False

    def _compute_today(self):
        for rec in self:
            rec.today = date.today()

    today = fields.Date(compute=_compute_today, compute_sudo=True)
    attachment_cv_id = fields.Many2many('ir.attachment', string="CV", required=False, )

    referred_partner_id = fields.Many2one('res.partner', string='Customer', )

    years_of_experience = fields.Float(string="Years of Experience", )

    job_offer_ids = fields.One2many('hr.job.offer', 'applicant_id')
    job_offers_count = fields.Integer(compute='_compute_job_offer_count', compute_sudo=True, store=True)

    interview_details_required = fields.Boolean(related='stage_id.interview_details_required',
                                                string='Interview Details Required')
    meeting_type = fields.Selection([
        ('online', 'Online'),
        ('offline', 'Offline'),
    ], string='Meeting Type' , default = 'online')
    meeting_link = fields.Char(string='Meeting Link')
    meeting_note = fields.Char()
    unavailable_room_ids = fields.Many2many('room.room', compute='_compute_unavailable_rooms')
    interview_day = fields.Date(string='Interview Date', tracking=True)

    interview_date = fields.Datetime(string='Interview Start (Computed)',
                                     compute='_compute_interview_datetimes',
                                     store=True,
                                     precompute=True)

    interview_date_to = fields.Datetime(string='Interview End (Computed)',
                                        compute='_compute_interview_datetimes',
                                        store=True,
                                        precompute=True)
    meeting_room = fields.Many2one('room.room', string="Room" ,default= False)

    team_id = fields.Many2one(
        'recruitment.team', required=False,
    )
    team_leader_ids = fields.Many2many(
        'res.users', related='team_id.team_leader_ids'
    )
    senior_id = fields.Many2one(
        related='team_id.senior_id', string='Team Leader'
    )
    assigned_team_leader_id = fields.Many2one(
        'res.users', domain="[('id', 'in',team_leader_ids)]",
        string='Assigned Interviewer'
    )
    created_employee = fields.Boolean(default=False)
    hide_create_action = fields.Boolean('hide action button', compute='compute_hide_action', compute_sudo=True,
                                        store=True)
    hide_generate_offer = fields.Boolean('hide generate offer', compute='compute_hide_action', compute_sudo=True,
                                         store=True)
    show_send_attachment_reminder = fields.Boolean('hide send reminder', compute='compute_reminder', compute_sudo=True)
    hide_salary = fields.Boolean('hide salary', compute='compute_hide_salary', compute_sudo=True, store=True)
    salary_proposed_extra = fields.Char("Proposed Salary Extra",
                                        help="Salary Proposed by the Organisation, extra advantages", tracking=True, )
    salary_expected_extra = fields.Char("Expected Salary Extra", help="Salary Expected by Applicant, extra advantages",
                                        tracking=True)
    salary_proposed = fields.Float("Proposed Salary", group_operator="avg", help="Salary Proposed by the Organisation",
                                   tracking=True,
                                   groups="nt_recruitment_update.expected_and_proposed_salary,nt_recruitment_update.group_hr_recruitment_ceo")
    salary_expected = fields.Float("Expected Salary", group_operator="avg", help="Salary Expected by Applicant",
                                   tracking=True,
                                   groups="nt_recruitment_update.expected_and_proposed_salary,nt_recruitment_update.group_hr_recruitment_ceo")
    ticket_count = fields.Integer('ticket count', compute='_compute_ticket_count', compute_sudo=True)
    work_email = fields.Char('Work Email')
    is_hide_create_offer = fields.Boolean('hide create job offer or not', comppute='compute_hide_create_job_offer',
                                          compute_sudo=True, store=True)
    feedback_applicant_ids = fields.One2many(
        'feedback.applicant',
        'hr_applicant_id'
    )
    name = fields.Char(related='partner_name')
    referral_by_email = fields.Char()

    ref_employee_id = fields.Many2one(
        'hr.employee', string='Referral By Employee', default=_default_ref_employee_id, )

    cv_link = fields.Char()
    stage_id = fields.Many2one('hr.recruitment.stage', readonly=False, store=True)
    feedback_required2 = fields.Boolean(compute='compute_the_stage_required_feedback', compute_sudo=True, store=True)
    employee_ids = fields.Many2many(comodel_name='hr.employee', string='Employees', store=True)
    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        related='job_id.department_id',
        store=True,
        tracking=True,
        readonly=False
    )

    def _get_time_selection(self):
        times = []
        for hour in range(8, 20):
            for minute in [0, 30]:
                value = f"{hour}:{minute:02d}"  # '8:00', '14:30'
                label = f"{hour:02d}:{minute:02d}"  # '08:00', '14:30'
                times.append((value, label))
        return times

    start_time = fields.Selection(
        selection=lambda self: self._get_time_selection(),
        string='Start Time',
    )
    end_time = fields.Selection(
        selection=lambda self: self._get_time_selection(),
        string='End Time',
    )

    def _parse_time(self, time_str):
        """Safely parse both old float format '14.5' and new string format '14:30'"""
        if not time_str:
            return None, None
        if ':' in time_str:
            # New format: '14:30'
            hour, minute = map(int, time_str.split(':'))
        else:
            # Old float format: '14.5'
            float_val = float(time_str)
            hour = int(float_val)
            minute = int(round((float_val - hour) * 60))
        return hour, minute

    @api.depends('interview_day', 'start_time', 'end_time')
    def _compute_interview_datetimes(self):
        for rec in self:
            if rec.interview_day and rec.start_time and rec.end_time:
                start_hour, start_minute = self._parse_time(rec.start_time)
                end_hour, end_minute = self._parse_time(rec.end_time)

                if start_hour is None or end_hour is None:
                    rec.interview_date = False
                    rec.interview_date_to = False
                    continue

                # Validation
                if (end_hour, end_minute) <= (start_hour, start_minute):
                    raise ValidationError("End Time must be after Start Time")

                # Build datetime
                dt_start = datetime.combine(
                    rec.interview_day,
                    time(hour=start_hour, minute=start_minute)
                )
                dt_end = datetime.combine(
                    rec.interview_day,
                    time(hour=end_hour, minute=end_minute)
                )

                # Timezone conversion
                user_tz = pytz.timezone(self.env.user.tz or 'UTC')
                dt_start_local = user_tz.localize(dt_start)
                dt_end_local = user_tz.localize(dt_end)

                rec.interview_date = dt_start_local.astimezone(pytz.utc).replace(tzinfo=None)
                rec.interview_date_to = dt_end_local.astimezone(pytz.utc).replace(tzinfo=None)
            else:
                rec.interview_date = False
                rec.interview_date_to = False
    # -----------------------------------
    # COMPUTE UNAVAILABLE ROOMS
    # -----------------------------------
    @api.depends('interview_date', 'interview_date_to')  # Depends on computed fields
    def _compute_unavailable_rooms(self):
        for rec in self:
            # Logic uses the computed interview_date and interview_date_to automatically
            if rec.interview_date and rec.interview_date_to:
                domain = [
                    ('start_datetime', '<', rec.interview_date_to),
                    ('stop_datetime', '>', rec.interview_date),
                ]
                booked_rooms = self.env['room.booking'].search(domain).mapped('room_id')

                # Exclude current applicant's existing booking from unavailable list
                if rec._origin.id and 'applicant_id' in self.env['room.booking']._fields:
                    my_booking = self.env['room.booking'].search([
                        ('applicant_id', '=', rec._origin.id)
                    ], limit=1)
                    if my_booking and my_booking.room_id in booked_rooms:
                        booked_rooms -= my_booking.room_id

                rec.unavailable_room_ids = booked_rooms
            else:
                rec.unavailable_room_ids = False

    # -----------------------------------
    # CONSTRAINT
    # -----------------------------------
    @api.constrains('meeting_room', 'interview_day', 'start_time', 'end_time')
    def _check_room_availability(self):
        for rec in self:
            _logger.warning(f"[APPLICANT CONSTRAINT] Checking applicant ID={rec.id}")

            # Check if all new fields are filled
            if not rec.meeting_room or not rec.interview_day or rec.start_time is None or rec.end_time is None:
                continue

            # 1. Check if Time is valid (End > Start)
            if rec.end_time <= rec.start_time:
                _logger.error("[TIME ERROR] End time must be after start time")
                raise ValidationError(_("End time must be after start time."))

            # 2. Check Datetime overlap (Uses computed fields)
            if rec.interview_date_to <= rec.interview_date:
                raise ValidationError(_("End date/time must be after start date/time."))

            domain = [
                ('room_id', '=', rec.meeting_room.id),
                ('start_datetime', '<', rec.interview_date_to),
                ('stop_datetime', '>', rec.interview_date),
            ]

            booking = self.env['room.booking'].search([
                ('applicant_id', '=', rec.id)
            ], limit=1)

            if booking:
                domain.append(('id', '!=', booking.id))

            conflict = self.env['room.booking'].search(domain, limit=1)

            if conflict:
                _logger.error(
                    f"[APPLICANT CONFLICT] Applicant={rec.id} "
                    f"conflict with booking={conflict.id}"
                )
                raise ValidationError(
                    _("The selected room is already booked for this time period.")
                )

    # -----------------------------------
    # CREATE / UPDATE BOOKING
    # -----------------------------------
    def _create_room_booking(self):
        """Create or update room booking for this applicant"""
        self.ensure_one()

        _logger.warning(f"[BOOKING EXECUTED] for applicant {self.id}")

        # This check now relies on the computed fields (interview_date & interview_date_to)
        # which will be False if the new inputs (day/time) are missing.
        if not self.meeting_room or not self.interview_date or not self.interview_date_to:
            _logger.warning("[BOOKING SKIPPED] Missing room or dates")
            return

        existing_booking = self.env['room.booking'].search([
            ('applicant_id', '=', self.id)
        ], limit=1)

        booking_vals = {
            'room_id': self.meeting_room.id,
            'booking_date': self.interview_day,  # Uses computed value
            'start_time': self.start_time,  # Uses computed value
            'end_time': self.end_time,  # Uses computed value
            'name': f'Interview - {self.partner_name or self.name}',
            'organizer_id': self.user_id.id or self.env.uid,
            'status': self.meeting_type,
            'applicant_id': self.id,
        }

        if existing_booking:
            existing_booking.write(booking_vals)
            _logger.warning(f"[BOOKING UPDATED] ID {existing_booking.id}")
        else:
            self.env['room.booking'].create(booking_vals)
            _logger.warning(f"[BOOKING CREATED] for applicant {self.id}")

    # -----------------------------------
    # WRITE
    # -----------------------------------
    def write(self, vals):
        _logger.warning(f"[APPLICANT WRITE] IDs={self.ids} vals keys={list(vals.keys())}")

        # --- Stage validation logic (من الكود القديم - لا يوجد تغيير) ---
        if vals.get('stage_id', False):
            for rec in self:
                if rec.stage_id.feedback_required:
                    if vals.get('feedback_applicant_ids', False):
                        stages = [line[2]['stage_id'] for line in vals['feedback_applicant_ids']]
                        if rec.stage_id.id not in stages:
                            raise ValidationError(_('Feedback is required.'))
                    else:
                        stages = [line.stage_id.id for line in rec.feedback_applicant_ids]
                        if rec.stage_id.id not in stages or not rec.feedback_applicant_ids:
                            raise ValidationError(_('Feedback is required.'))

                stage_move = self.env['stage.move'].search([('hr_applicant_id', '=', rec.id)], limit=1)
                if rec.stage_id.interview_details_required and not stage_move:
                    raise ValidationError(_('Please fill the interview details.'))

            stage_ids = self.env['hr.recruitment.stage'].browse(vals['stage_id'])
            if stage_ids and stage_ids.required_activity:
                self.env['mail.activity'].create({
                    'res_id': self.id,
                    'res_model': 'hr.applicant',
                    'res_model_id': self.env['ir.model'].search([('model', '=', 'hr.applicant')]).id,
                    'activity_type_id': stage_ids.activity_type_id.id,
                    'summary': 'An Activity Created for this Application',
                    'date_deadline': fields.Date.today() + relativedelta(days=5),
                    'user_id': self.env.uid,
                })

        # --- Single super() call ---
        res = super(HrApplicant, self).write(vals)

        # --- Booking logic (تم التعديل هنا) ---
        # 1. قمنا بتغيير booking_fields ليشمل الحقول الجديدة
        # 2. تمت إزالة interview_date و interview_date_to لأنهم computed ولن يأتوا في vals

        booking_fields = {'meeting_room', 'interview_day', 'start_time', 'end_time'}

        if booking_fields.intersection(vals.keys()):
            for rec in self:
                _logger.warning(
                    f"[WRITE TRIGGER] Applicant={rec.id} "
                    f"room={rec.meeting_room.id if rec.meeting_room else None} "
                    f"start={rec.interview_date} end={rec.interview_date_to}"
                )
                # ملاحظة: rec.interview_date هنا ستعمل بشكل صحيح
                # لأن super().write تم تنفيذه بالأعلى، وبالتالي ال computed fields تم تحديثها بالقيم الجديدة

                if rec.meeting_room and rec.interview_date and rec.interview_date_to:
                    rec._create_room_booking()
                else:
                    # إذا تم مسح الغرفة أو التاريخ، قم بحذف الحجز
                    booking = self.env['room.booking'].search([('applicant_id', '=', rec.id)], limit=1)
                    if booking:
                        booking.unlink()

        return res
        
    @api.model_create_multi
    def create(self, vals_list):
        _logger.warning(f"[APPLICANT CREATE] vals_list count={len(vals_list)}")

        records = super().create(vals_list)

        for rec in records:
            _logger.warning(
                f"[APPLICANT CREATE] rec={rec.id} "
                f"room={rec.meeting_room.id if rec.meeting_room else None} "
                f"start={rec.interview_date} end={rec.interview_date_to}"
            )
            if rec.meeting_room and rec.interview_date and rec.interview_date_to:
                _logger.warning(f"[CREATE] Triggering booking for applicant={rec.id}")
                rec._create_room_booking()

        return records
        
        
    @api.depends('stage_id.job_offer', 'stage_id')
    def compute_hide_create_job_offer(self):
        for rec in self:
            if rec.stage_id.job_offer:
                rec.is_hide_create_offer = False
            else:
                rec.is_hide_create_offer = True

    @api.depends('job_offer_ids')
    def _compute_ticket_count(self):
        for rec in self:
            ticket_count = self.env['helpdesk.ticket'].sudo().search_count([('app_id', '=', rec.id)])
            if ticket_count:
                rec.ticket_count = ticket_count
            else:
                rec.ticket_count = 0

    @api.depends('stage_id.show_send_reminder')
    def compute_reminder(self):
        for rec in self:
            if rec.sudo().stage_id.show_send_reminder:
                rec.sudo().show_send_attachment_reminder = True
            else:
                rec.sudo().show_send_attachment_reminder = False

    @api.constrains('salary_proposed', 'stage_id', 'work_email')
    def _check_values(self):
        if self.salary_proposed == 0.00 and self.stage_id.job_offer:
            raise ValidationError(_('Proposed Salary Value should not be zero.'))
        if not self.work_email and self.stage_id.job_offer:
            raise ValidationError(_('Work Email Required.'))


    @api.depends()
    def compute_hide_salary(self):
        for rec in self:
            if self.env.user.has_group('hr_recruitment.group_hr_recruitment_user'):
                rec.hide_salary = True
            else:
                rec.hide_salary = False

    @api.depends('stage_id.job_offer', 'job_offer_ids.state')
    def compute_hide_action(self):
        for rec in self:
            if not rec.stage_id.job_offer:
                rec.hide_create_action = True
            else:
                rec.hide_create_action = False
                if rec.job_offer_ids:
                    for obj in rec.job_offer_ids:
                        if obj.state not in ['done', 'reject']:
                            rec.hide_create_action = True
                        else:
                            rec.hide_create_action = False
            if rec.application_status == 'hired':
                rec.hide_create_action = True

    @api.onchange('team_id')
    def get_assigned_team_leader_id(self):
        for rec in self:
            if rec.team_id.team_leader_ids:
                rec.assigned_team_leader_id = rec.team_id.team_leader_ids[0].id

    @api.onchange('user_id')
    def onchange_user_id(self):
        user = self.job_id.user_id.id
        return {'domain': {'user_id': [('id', '=', user)]}}

    def action_get_attachment_tree_view(self):
        action = self.env['ir.actions.act_window'].sudo()._for_xml_id('base.action_attachment')
        action['context'] = {'default_res_model': self._name, 'default_res_id': self.ids[0]}
        action['domain'] = str(['&', ('res_model', '=', self._name), ('res_id', 'in', self.ids)])
        action['search_view_id'] = (self.env.ref('hr_recruitment.ir_attachment_view_search_inherit_hr_recruitment').id,)
        return action

    @api.depends('stage_id', 'stage_id.feedback_required')
    def compute_the_stage_required_feedback(self):
        for rec in self:
            if rec.stage_id:
                rec.feedback_required2 = rec.stage_id.feedback_required

    def create_job_offer_from_applicant(self):
        offer_id = self.env['hr.job.offer'].create({
            'applicant_id': self.id,
            'employee_id': self.emp_id.id,
            'company_id': self.company_id.id,
            # 'prepaid_by': self.user_id.id,
            'offer_date': fields.Date.today(),
            # 'availability_date': fields.Date.today(),
            'monthly_salary': self.salary_proposed
        })
        self.job_offer_ids = [Command.link(offer_id.id)]
        for offer in self.job_offer_ids:
            if offer.state == 'done':
                return {
                    'type': 'ir.actions.act_window',
                    'name': _('Cancel Job Offer'),
                    'res_model': 'cancel.job.offer.wiz',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {'current_id': self.id},
                    'views': [[False, 'form']]
                }

    @api.onchange('job_id')
    def _onchange_job_id(self):
        """ job_id """
        self.team_id = self.job_id.recruitment_team_id.id

    @api.depends('job_id')
    def _compute_user(self):
        for applicant in self:
            applicant.user_id = applicant.job_id.user_id.id or None

    @api.onchange('referral_by_email')
    def _onchange_referral_by_email(self):
        """ referral_by_email """
        if self.referral_by_email:
            emp = self.env['hr.employee'].search(
                [('work_email', '=', self.referral_by_email)], limit=1)
            if emp:
                self.ref_employee_id = emp.id


    def _inverse_partner_email(self):
        for applicant in self:
            ...


    def create_employee_from_applicant(self):
        """ Create an hr.employee from the hr.applicants """
        employee = False
        for applicant in self:
            contact_name = False
            if applicant.partner_id:
                address_id = applicant.partner_id.address_get(['contact'])[
                    'contact']
                contact_name = applicant.partner_id.display_name
            else:
                if not applicant.partner_name:
                    raise UserError(
                        _('You must define a Contact Name for this applicant.'))

                new_partner_id = self.env['res.partner'].sudo().create({
                    'is_company': False,
                    'type': 'private',
                    'name': applicant.partner_name,
                    'email': applicant.email_from,
                    'phone': applicant.partner_phone,
                    'mobile': applicant.partner_mobile,
                })
                applicant.partner_id = new_partner_id

                address_id = new_partner_id.address_get(['contact'])['contact']
            if applicant.partner_name or contact_name:
                employee_data = {
                    'default_name': applicant.partner_name or contact_name,
                    'default_job_id': applicant.job_id.id,
                    'default_job_title': applicant.job_id.name,
                    # 'address_id': address_id,
                    'default_department_id': applicant.department_id.id or False,
                    'default_address_id': applicant.company_id and applicant.company_id.partner_id
                                          and applicant.company_id.partner_id.id or False,
                    'default_work_email': applicant.department_id and applicant.department_id.company_id
                                          and applicant.department_id.company_id.email or False,
                    'default_work_phone': applicant.department_id.company_id.phone,
                    'form_view_initial_mode': 'edit',
                    'default_applicant_id': applicant.ids,
                    'default_ref_employee_id': applicant.ref_employee_id.id,
                    'default_referral_by_email': applicant.referral_by_email,
                    'ref_employee_id': applicant.ref_employee_id,
                    'referral_by_email': applicant.referral_by_email,
                    'categ_ids': applicant.categ_ids,
                    'referred_partner_id': applicant.referred_partner_id.id,
                    # 'default_in_probation_period': True,
                    'default_date_start': applicant.availability,

                }
        dict_act_window = self.env['ir.actions.act_window']._for_xml_id(
            'hr.open_view_employee_list')
        dict_act_window['context'] = employee_data
        return dict_act_window

    @api.onchange('stage_id')
    def _check_stage(self):
        if self.stage_id.hired_stage:
            if not self.emp_id:
                address_id = self.partner_id.address_get(['contact'])[
                    'contact']
                contact_name = self.partner_id.display_name
                date = None
                if self.availability:
                    date = self.availability + relativedelta(months=3)
                referral_categ = self.env['hr.applicant.category'].browse(self.categ_ids.ids)
                employee = self.env['hr.employee'].search([
                    ('name', '=', self.partner_name or contact_name),
                    ('job_id', '=', self.job_id.id),
                    ('job_title', '=', self.job_id.name),
                    ('address_id', '=', address_id),
                    ('department_id', '=', self.department_id.id or False),
                    ('address_id', '=', self.company_id.id and self.company_id.partner_id
                     and self.company_id.partner_id.id or False),
                    ('work_email', '=', self.department_id and self.department_id.company_id
                     and self.department_id.company_id.email or False,),
                    ('work_phone', '=', self.department_id.company_id.phone),
                    ('applicant_id', '=', self.id),
                    ('ref_employee_id', '=', self.ref_employee_id.id),
                    ('referral_by_email', '=', self.referral_by_email),
                    ('referred_partner_id', '=', self.referred_partner_id.id),
                    ('date_start', '=', self.availability),
                ])

                if not employee:
                    ###############################################################
                    default_user = self.env.ref('base.default_user', raise_if_not_found=False)

                    user_vals = {
                        'is_company': False,
                        'name': self.partner_name,
                        'login': self.work_email,
                        'email': self.work_email,
                        'mobile': self.partner_mobile,
                        'phone': self.partner_phone,
                        'groups_id': [(4, self.env.ref('base.group_user').id)],
                        'contact_type': 'contact',
                    }

                    if default_user and not default_user.active:
                        default_user = default_user.with_context(active_test=False)
                        user_vals.update({
                            'active': True,
                        })

                        user = default_user.sudo().copy(user_vals)
                    else:
                        user = self.env['res.users'].sudo().create(user_vals)

                    self.partner_id = user.partner_id.id
                    # self.partner_id.is_center = False
                    self.partner_id.property_account_receivable_id = int(
                        self.env['ir.config_parameter'].sudo().get_param(
                            'ResConfigSettings.recruitment_account_receivable', 0))
                    self.partner_id.property_account_payable_id = int(self.env['ir.config_parameter'].sudo().get_param(
                        'ResConfigSettings.recruitment_account_payable', 0))

                    category = self.env['res.partner.category'].sudo().search_read([('name', '=', 'Hr Applicant')],
                                                                                   ['id'],
                                                                                   limit=1)
                    if category:
                        self.partner_id.category_id = [(4, category[0]['id'])]
                    else:
                        hr_applicant_category = self.env['res.partner.category'].create({'name': 'Hr Applicant'})
                        self.partner_id.category_id = [(4, hr_applicant_category[0]['id'])]

                    ################################################################
                    employee_data = {
                        'name': self.partner_name or contact_name,
                        'job_id': self.job_id.id,
                        'job_title': self.job_id.name,
                        'department_id': self.department_id.id or False,
                        'address_id': self.company_id.id and self.company_id.partner_id
                                      and self.company_id.partner_id.id or False,
                        'work_email': self.work_email or False,
                        'work_phone': self.department_id.company_id.phone if self.department_id else self.partner_phone,
                        'applicant_id': self.ids,
                        'ref_employee_id': self.ref_employee_id.id,
                        'referral_by_email': self.referral_by_email,
                        'referred_partner_id': self.referred_partner_id.id,
                        'date_start': self.availability if self.availability else fields.Datetime.today(),
                        'probation_period_end_date': date,
                        'date_end': None,
                        # 'related_partner_id': self.partner_id,
                        'user_id': user.id,

                    }
                    if referral_categ:
                        employee_data.update({'categ_ids': [(6, 0, referral_categ.ids)]})

                    new_emp = self.env['hr.employee'].sudo().create(employee_data)

                    self.emp_id = new_emp.id
                    attachment = self.env['ir.attachment'].sudo().search(
                        [('res_id', '=', self.id)])
                    if attachment:
                        attachment.sudo().write({'res_model': 'hr.employee', 'res_id': new_emp.id})

                else:
                    pass
            else:
                raise ValidationError(_('The Employee has been created!'))

    @api.constrains('partner_mobile', 'partner_phone')
    def _check_mobile_phone(self):
        """ Validate mobile and phone """
        for rec in self:
            if rec.partner_mobile == rec.partner_phone and rec.partner_mobile and rec.partner_phone:
                raise ValidationError(
                    _("The mobile must be different from the phone"))
            if rec.partner_mobile:
                partner_mobile = self.env['hr.applicant'].search(
                    [('id', '!=', rec.id), '|',
                     ('partner_mobile', '=', rec.partner_mobile),
                     ('partner_phone', '=', rec.partner_mobile)]
                )
                if partner_mobile:
                    raise ValidationError(_('Mobile must be unique'))

            if rec.partner_phone:
                partner_phone = self.env['hr.applicant'].search(
                    [('id', '!=', rec.id), '|',
                     ('partner_phone', '=', rec.partner_phone),
                     ('partner_mobile', '=', rec.partner_phone)]
                )
                if partner_phone:
                    raise ValidationError(_('Phone must be unique'))

    def open_stages_applicant(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Stage Move'),
            'res_model': 'stage.move',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_hr_applicant_id': self.id,
                'default_current_stage_id': self.stage_id.id,
                # 'default_salary_expected': self.salary_expected,
                'default_interview_date': self.interview_date,
                'default_meeting_type': self.meeting_type,
                'default_meeting_link': self.meeting_link,
                'default_meeting_note': self.meeting_note,

            },
            'views': [[False, 'form']]
        }

    def archive_applicant(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Refuse Reason'),
            'res_model': 'applicant.get.refuse.reason',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_applicant_ids': self.ids,
                        'default_applicant_id': self.id,
                        'active_test': False},
            'views': [[False, 'form']]
        }

    def send_attachment_reminder_manually(self):
        for rec in self:
            rec.sudo().message_post_with_source('nt_recruitment_update.email_template_attahcment_reminder', **{
                'subtype_id': self.env['ir.model.data'].sudo()._xmlid_to_res_id('mail.mt_note'),
                'email_layout_xmlid': 'mail.mail_notification_light',
            })
            # mail_template = self.sudo().env.ref('nt_recruitment_update.email_template_attahcment_reminder')
            # mail_template.send_mail(self.id, force_send=True)

    def send_attachment_reminder(self):
        """
        Send reminder email to applicant with the url that ge can upload attachments

        """
        records = self.sudo().search([])
        for rec in records:
            if rec.availability:
                diff = fields.Datetime.now().date() - rec.availability
                contract_probosal_stg = self.env.ref(
                    'hr_recruitment.stage_job4')  # this is contract probosal stage (check hr_recruitment_data file in hr_recruitment )
                if rec.stage_id.id == contract_probosal_stg.id and diff.days == 10:
                    rec.sudo().message_post_with_source('nt_recruitment_update.email_template_attahcment_reminder', **{
                        'auto_delete_message': True,
                        'subtype_id': self.env['ir.model.data'].sudo()._xmlid_to_res_id('mail.mt_note'),
                        'email_layout_xmlid': 'mail.mail_notification_light'
                    })

    @api.depends('job_offer_ids')
    def _compute_job_offer_count(self):
        for rec in self:
            job_offers_count = self.env['hr.job.offer'].sudo().search_count([('applicant_id', '=', rec.id)])
            rec.job_offers_count = job_offers_count

    def action_show_job_offers(self):
        return {
            'name': 'Job Offers',
            'type': 'ir.actions.act_window',
            'res_model': 'hr.job.offer',
            'view_mode': 'list,form',
            'domain': [('applicant_id', '=', self.id)]
        }

    def action_open_ticket(self):
        self.ensure_one()
        return {
            'name': 'help desk ticket',
            'type': 'ir.actions.act_window',
            'res_model': 'helpdesk.ticket',
            'view_mode': 'list,form',
            'domain': [('app_id', '=', self.id)]

        }

    # def website_form_input_filter(self, request, values):
    #     res = super(HrApplicant, self).website_form_input_filter(request, values)
    #     values['salary_expected'] = request.params['salary_expected']
    #     values['years_of_experience'] = request.params['years_of_experience']
    #     values['availability'] = request.params['availability']
    #     return res

    # def create_on_boarding_ticket(self, app_id):
    #     """"create help desk ticket for new employee """
    #     self.ensure_one()
    #     boarding_stages = self.env['boarding.stage'].search([])
    #     if boarding_stages:
    #         for rec in boarding_stages:
    #             department = rec.department_id
    #             responsable = rec.responsible_id
    #             description = rec.description
    #             category = rec.category
    #             help_disk_team = rec.help_desk_team
    #             name = rec.name
    #             self.env['helpdesk.ticket'].create({
    #                 'name': name,
    #                 'team_id': help_disk_team.id,
    #                 'category_id': category.id,
    #                 'user_id': self.ref_employee_id.id,
    #                 'description_html': description,
    #                 'app_id': app_id
    #             })


class FeedbackApplicant(models.Model):
    """
        Initialize Feedback Applicant:
         -
    """
    _name = 'feedback.applicant'
    _description = 'Feedback Applicant'
    _check_company_auto = True

    feedback = fields.Text(
        translate=True,
    )
    user_id = fields.Many2one(
        'res.users', default=lambda self: self.env.user, readonly=True
    )
    hr_applicant_id = fields.Many2one(
        'hr.applicant'
    )
    stage_id = fields.Many2one('hr.recruitment.stage')

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if not record.stage_id:
                record.stage_id = record.hr_applicant_id.stage_id.id
        return records
