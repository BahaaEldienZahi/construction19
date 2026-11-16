""" Initialize Helpdesk Ticket """

from odoo import _, api, fields, models, tools
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from datetime import date, datetime

field_to_change_mapping = {
    'stage_id': 'change_stage',
    'team_id': 'change_team',
    'user_id': 'change_assigned',
    'priority': 'change_priority',
    'helpdesk_area_id': 'change_area',
    'category_id': 'change_category',
    'ticket_type_id': 'change_type',
    'tag_ids': 'change_tags',
}


class HelpdeskTicket(models.Model):
    """
        Inherit Helpdesk Ticket:
         -
    """
    _inherit = 'helpdesk.ticket'

    department_is_set = fields.Boolean()
    team_id = fields.Many2one('helpdesk.ticket.team', store=True, tracking=True, default=False)
    categ_ids = fields.Many2many(comodel_name="helpdesk.category", related="team_id.helpdesk_categ_ids", string="", )
    category_id = fields.Many2one('helpdesk.category', store=True, ondelete='set null',
                                  domain="[('id', 'in', categ_ids)]", tracking=True)
    sub_category_ids = fields.Many2many(
        'helpdesk.category', tracking=True,
        domain="[('parent_id', '=',category_id),('parent_id', '!=',None)]"
    )
    product_id = fields.Many2one('product.product', tracking=True, store=True)
    product_tmpl_id = fields.Many2one(related='product_id.product_tmpl_id')

    project_id = fields.Many2one(
        'project.project', domain="[('partner_id', '=', partner_id)]",
        groups='helpdesk_mgmt.group_helpdesk_user,nt_helpdesk.group_helpdesk_technical_user',
        tracking=True, store=True
    )
    project_code = fields.Char(
        related='project_id.code', string="Project Code", tracking=True, related_sudo=True,
    )
    customer_code = fields.Char(
        related='partner_id.ref', string="Customer Ref", tracking=True,
    )
    date = fields.Datetime(
        default=fields.Datetime.now(), tracking=True
    )
    due_date = fields.Date(tracking=True)
    image = fields.Binary()
    employee_id = fields.Many2one('hr.employee', readonly=False,
                                  default=lambda self: self.env['hr.employee'].sudo().search(
                                      [('user_id', '=', self.env.uid)], limit=1),
                                  )
    employee_work_phone = fields.Char(related='employee_id.mobile_phone', readonly=True, related_sudo=True)
    member_ids = fields.Many2many(related='team_id.user_ids', related_sudo=True)

    ticket_type_id = fields.Many2one('helpdesk.ticket.type', tracking=True)
    company_id = fields.Many2one('res.company', tracking=True)
    tag_ids = fields.Many2many('helpdesk.ticket.tag', tracking=True)
    priority = fields.Selection(tracking=True, default=False)
    sla_deadline = fields.Datetime(tracking=True)
    partner_id = fields.Many2one('res.partner', tracking=True)
    partner_name = fields.Char(tracking=True)
    partner_email = fields.Char(tracking=True)
    email_cc = fields.Char(tracking=True)

    description = fields.Text()
    description_html = fields.Html()

    sequence = fields.Integer(related='stage_id.sequence')

    to_check_team_id = fields.Many2one('helpdesk.ticket.team', string='To Check Team')
    to_check_user_id = fields.Many2one('res.users', string='To Check user')

    app_create_uid = fields.Many2one('res.users', string='App Create By')

    ticket_type_ids = fields.Many2many(related='team_id.helpdesk_ticket_type_ids', related_sudo=True)

    area_ids = fields.Many2many(related='team_id.helpdesk_area_ids', related_sudo=True)
    helpdesk_area_id = fields.Many2one('helpdesk.area', store=True)

    product_ids = fields.Many2many(related='team_id.helpdesk_product_ids', related_sudo=True)
    helpdesk_product_id = fields.Many2one('product.template', domain="[('sale_ok','=',True)]", string='Products')

    helpdesk_attachment_ids = fields.One2many(comodel_name="helpdesk.attachment", inverse_name="ticket_id", string="Tickets",
                                              required=False, )
    area = fields.Boolean(string="Area", related='team_id.area', related_sudo=True)
    external = fields.Boolean(string="External", related='team_id.external', store=True)
    checked_area = fields.Boolean(default=False)
    change_stage_date = fields.Date(compute="compute_change_stage_date", store=True)

    last_team_id = fields.Many2one(comodel_name="helpdesk.ticket.team", string="Last Team", store=True,
                                   required=False, )
    first_user_id = fields.Many2one(comodel_name="res.users", string="First user", store=True, required=False,
                                    compute='compute_first_user_id')

    ticket_log_ids = fields.One2many(comodel_name="helpdesk.ticket.log", inverse_name="ticket_id", string="Ticket Log",
                                     required=False, )

    invisible_fields = fields.Char(string="Invisible Fields", compute="compute_invisible_required_fields",
                                   required=False, store=True)
    required_fields = fields.Char(string="Required Fields", compute="compute_invisible_required_fields", required=False,
                                  store=True)
    domain_team_ids = fields.Many2many(comodel_name="helpdesk.ticket.team", compute="compute_domain_team_ids", string="", )

    user_ids = fields.Many2many('res.users', 'res_users_team_rel', 'user_id', 'team_id', 'Related Users',
                                compute='compute_related_user_ids_from_team', store=True)
    team_project = fields.Many2one('helpdesk.ticket.team', string=" Team Project", store=True)
    team_project_required = fields.Boolean(string="Team Project Required", compute="compute_team_project_required")
    recurred_issue = fields.Boolean(string="Recurred Issue", copy=False)
    recurred_issue_ref = fields.Char(string="Recurred Issue Ref", copy=False)
    any_desk_id = fields.Char('AnyDesk')
    cr_number = fields.Char('CR #')
    required_project_team_id = fields.Boolean( related='team_id.required_project_team_id', store=True)
    required_stage_id = fields.Many2one('helpdesk.ticket.stage', related='team_id.required_stage_id', store=True)
    helpdesk_cr_ids = fields.Many2many(
        'helpdesk.cr',
        'helpdesk_ticket_cr_rel',
        'ticket_id',
        'cr_id',
        string='CR #'
    )
    work_item_ids = fields.Many2many('helpdesk.cr', string='Work Items #')

    @api.depends('message_ids', 'user_id')
    def compute_first_user_id(self):
        for rec in self:
            if not rec.first_user_id:
                if rec.message_ids:
                    subtype_id = self.env.ref('nt_helpdesk.helpdesk_change_fields', raise_if_not_found=False)
                    if not subtype_id:
                        rec.first_user_id = rec.user_id.id
                        continue
                    first_message_with_assign = rec.message_ids.filtered(
                        lambda msg: msg.subtype_id == subtype_id and msg.sudo().tracking_value_ids[
                            0].field_id.name == 'user_id')
                    if first_message_with_assign:
                        rec.first_user_id = first_message_with_assign[-1].sudo().tracking_value_ids[0].new_value_integer
                    else:
                        rec.first_user_id = rec.user_id.id
                else:
                    rec.first_user_id = rec.user_id.id

    @api.depends('team_id', 'team_id.is_team_project')
    def compute_team_project_required(self):
        for rec in self:
            if rec.team_id.is_team_project:
                rec.team_project_required = True
            else:
                rec.team_project_required = False

    @api.depends('team_id', 'team_id.department_ids', 'team_id.team_user_ids', 'team_id.assigned_user_id')
    def compute_related_user_ids_from_team(self):
        for rec in self:
            if rec.team_id.team_user_ids:
                rec.sudo().user_ids += rec.team_id.team_user_ids
            if rec.team_id.department_ids:
                member_ids = rec.sudo().team_id.department_ids.member_ids
                rec.user_ids = [(6, 0, [member_id.user_id.id for member_id in member_ids])]
            if rec.team_id.assigned_user_id:
                rec.user_ids += rec.sudo().team_id.assigned_user_id
            rec.user_ids += rec.sudo().env.user
            rec.user_ids += rec.sudo().create_uid

    default_user = fields.Boolean(store=True)
    readonly_assign = fields.Boolean(compute="_compute_assign_readonly")

    # readonly_tl_assign =

    @api.depends('team_id')
    def _compute_assign_readonly(self):
        team_member = []
        is_manager = False
        department_obj = self.env['hr.department'].search([('id', 'in', self.team_id.department_ids.ids)])
        for rec in self:
            rec.readonly_assign = True
            for dept in department_obj:
                for emp in dept.member_ids:
                    team_member.append(emp.user_id.id)
                    if self.env.user.id != dept.manager_id.id:
                        is_manager = True
            if not self.env.user.has_group('helpdesk_mgmt.group_helpdesk_manager') or is_manager:
                if self.env.user.id not in team_member or self.env.user.id not in rec.team_id.assign_user_ids.ids:
                    rec.readonly_assign = True
                else:
                    rec.readonly_assign = False
            # [FIX] allow team member to edit assigned to
            if rec.team_id:
                team_users = rec.team_id.team_user_ids.user_ids.ids
                # if self.env.user.id in team_users:
                #     rec.readonly_assign = False
                if self.env.user.id in rec.team_id.assign_user_ids.ids:
                    rec.readonly_assign = False

    user_id = fields.Many2one(
        'res.users', string='Assigned to', store=True,
        readonly=False, tracking=True, domain="[('id', 'in', user_ids)]")

    domain_sub_area_ids = fields.Many2many(comodel_name="helpdesk.area", relation="sub_area_ids",
                                           compute="compute_domain_sub_area_ids", string="", )
    sub_area_id = fields.Many2one(comodel_name="helpdesk.area", string="Sub Area", )

    ticket_tag = fields.Selection(string="Ticket Tag", selection=[('internal', 'Internal'), ('portal', 'Portal'), ],
                                  required=False, )
    support_log = fields.Text(string="Support log", )
    department_id = fields.Many2one(comodel_name="hr.department", string="Department", store="True",
                                    related="create_uid.department_id", required=False, related_sudo=True)
    to_check_date = fields.Datetime(copy=False, compute='compute_to_check_date', store=True)
    close_date = fields.Datetime(compute='compute_close_date', store=True, copy=False)

    @api.depends('message_ids')
    def compute_close_date(self):
        subtype_id = self.env.ref('nt_helpdesk.helpdesk_change_fields', raise_if_not_found=False)
        for rec in self:
            if subtype_id and rec.message_ids:
                last_message_with_to_close = rec.message_ids.filtered(
                    lambda msg: msg.subtype_id == subtype_id and msg.sudo().tracking_value_ids[
                        0].field_id.name == 'stage_id'
                                and msg.sudo().tracking_value_ids[0].new_value_char == 'Solved')
                if last_message_with_to_close:
                    rec.close_date = last_message_with_to_close[0].date

    @api.depends('message_ids', )
    def compute_to_check_date(self):
        subtype_id = self.env.ref('nt_helpdesk.helpdesk_change_fields', raise_if_not_found=False)
        for rec in self:
            if subtype_id and rec.message_ids:
                last_message_with_to_check = rec.message_ids.filtered(
                    lambda msg: msg.subtype_id == subtype_id and msg.sudo().tracking_value_ids[
                        0].field_id.name == 'stage_id'
                                and msg.sudo().tracking_value_ids[0].new_value_char == 'To Check')
                if last_message_with_to_check:
                    rec.to_check_date = last_message_with_to_check[0].date

    @api.depends('helpdesk_area_id')
    def compute_domain_sub_area_ids(self):
        for rec in self:
            if rec.helpdesk_area_id:
                sub_areas = self.env['helpdesk.area'].search([('parent_id', '=', rec.helpdesk_area_id.id)])
                rec.domain_sub_area_ids = sub_areas.ids
            else:
                rec.domain_sub_area_ids = False

    @api.depends('external')
    def compute_domain_team_ids(self):
        for rec in self:
            if rec.external:
                team_ids = self.env['helpdesk.ticket.team'].search([('external', '=', True)])
                rec.domain_team_ids = team_ids.ids
            else:
                team_ids = self.env['helpdesk.ticket.team'].search([])
                rec.domain_team_ids = team_ids.ids

    @api.depends('team_id', 'team_id.invisible_field_ids', 'team_id.required_field_ids', 'team_id.helpdesk_required_field_ids')
    def compute_invisible_required_fields(self):
        for rec in self:
            invisible_field_list = []
            required_field_list = []
            if rec.team_id:
                for invisible in rec.team_id.invisible_field_ids:
                    invisible_field_list.append(invisible.name)
                for required in rec.team_id.required_field_ids:
                    required_field_list.append(required.name)
                for required in rec.team_id.helpdesk_required_field_ids:
                    required_field_list.append(required.name)
            rec.invisible_fields = invisible_field_list
            rec.required_fields = required_field_list
        if len(self) == 1:
            new_stage = self.env['helpdesk.ticket.stage'].sudo().search([('sequence', '=', 0)], limit=1)
            current_stage = self.env['helpdesk.ticket.stage'].sudo().search(
                [('id', '=', self.stage_id.id)],
                limit=1)
            global_stage = self.env['helpdesk.ticket.stage'].sudo().search(
                [('is_global', '=', True)],
                limit=1)

            close_stage = self.env['helpdesk.ticket.stage'].sudo().search(
                [('is_close', '=', True)],
                limit=1)
            reopen_stage = self.env['helpdesk.ticket.stage'].sudo().search(
                [('is_reopen', '=', True)],
                limit=1)

            if current_stage.sequence != 0 and current_stage.id not in [global_stage.id, close_stage.id,
                                                                        reopen_stage.id]:
                if new_stage:
                    self.stage_id = new_stage.id

    @api.onchange('helpdesk_product_id')
    def onchange_helpdesk_product_id(self):
        for rec in self:
            rec.category_id = rec.helpdesk_product_id.helpdesk_category_id.id

    @api.onchange('team_id')
    def _onchange_department_id(self):
        if not self.team_id.external:
            self.user_id = None
        else:
            self.sudo().user_id = self.sudo().team_id.assigned_user_id or self.env.user

    @api.onchange('partner_id')
    def _onchange_partner(self):
        """ Partner"""
        self.project_id = False

    @api.onchange('user_id', 'partner_id')
    def _onchange_user_id(self):
        """ user_id """
        if self.user_id and self.id:
            if not self.partner_id:
                raise ValidationError(_('You must select the customer first'))

    def _track_subtype(self, init_values):
        self.ensure_one()
        if init_values:
            return self.env.ref(
                'nt_helpdesk.helpdesk_change_fields')
        return super(HelpdeskTicket, self)._track_subtype(init_values)

    @api.depends('stage_id')
    def compute_change_stage_date(self):
        for rec in self:
            rec.change_stage_date = date.today()

    def ticket_stage_reminder_cron(self):
        close_stage = self.env['helpdesk.ticket.stage'].search([('is_close', '=', True)], limit=1)
        global_stage = self.env['helpdesk.ticket.stage'].search([('is_global', '=', True)])
        open_tickets = self.env['helpdesk.ticket'].search([('stage_id', 'in', global_stage.ids)])
        today = date.today()
        for ticket in open_tickets:
            change_stage_date_before_15_day = ticket.change_stage_date + relativedelta(days=15)
            change_stage_date_before_30_day = ticket.change_stage_date + relativedelta(days=30)
            res_model_id = self.env['ir.model'].search([('name', '=', self._description)]).id
            activity_type_id = self.env.ref('mail.mail_activity_data_todo').id
            if today == change_stage_date_before_15_day:
                self.env['mail.activity'].create([{
                    'activity_type_id': activity_type_id,
                    'date_deadline': fields.Datetime.today(),
                    'summary': f"the ticket no {ticket.name} still in stage {ticket.stage_id.name} since 15 days.",
                    'user_id': ticket.sudo().user_id.id,
                    'res_id': ticket.id,
                    'res_model_id': res_model_id,
                }])
            if today == change_stage_date_before_30_day:
                self.env.cr.execute("UPDATE helpdesk_ticket SET stage_id=%s WHERE id=%s;" % (
                    close_stage.id, ticket.id))
                # ticket.sudo().write({'stage_id': close_stage.id})

    @api.model
    def create(self, vals_list):
        """ Override create """
        res = super(HelpdeskTicket, self).create(vals_list)
        if vals_list.get('team_id'):
            vals_list.update(department_is_set=True)
        if vals_list.get('partner_id'):
            for line in res.sudo().message_follower_ids:
                if res.partner_id == line.partner_id:
                    res.message_follower_ids = [(2, line.id)]
        res.sudo().checked_area = True
        res.sudo().last_team_id = res.sudo().team_id.id
        if 'partner_id' in res:
            if res.partner_id:
                is_partner_id_follower = self.env["mail.followers"].sudo().search([
                    ('res_model', '=', 'helpdesk.ticket'),
                    ('res_id', '=', res.id),
                    ('partner_id', '=', res.sudo().partner_id.id)
                ])
                if not is_partner_id_follower:
                    self.env["mail.followers"].sudo().create(
                        {
                            "res_model": "helpdesk.ticket",
                            "res_id": res.id,
                            "partner_id": res.sudo().partner_id.id,
                        }
                    )
        odoo_boot = self.env.ref('base.user_root')
        if self.env.user.has_group('base.group_user') and self.env.user.id != odoo_boot.id:
            res.sudo().ticket_tag = 'internal'
        else:
            res.sudo().ticket_tag = 'portal'
            # customer_followers = res.sudo().partner_id.allowed_users.filtered(
            #     lambda line: line.team_id == res.team_id).mapped('user_ids')
            # if customer_followers:
            #     for user in customer_followers:
            #         is_partner_id_follower = self.env["mail.followers"].sudo().search([
            #             ('res_model', '=', 'helpdesk.ticket'),
            #             ('res_id', '=', res.id),
            #             ('partner_id', '=', user.sudo().partner_id.id)
            #         ])
            #         if not is_partner_id_follower:
            #             self.env["mail.followers"].sudo().create(
            #                 {
            #                     "res_model": "helpdesk.ticket",
            #                     "res_id": res.id,
            #                     "partner_id": user.sudo().partner_id.id,
            #                 }
            #             )
        # self.env['helpdesk.ticket.log'].sudo().create(data)
        self._patch_cr_records()
        return res

    def write(self, vals):
        """ Override write """
        for rec in self:
            if rec.area and rec.checked_area and not rec.helpdesk_area_id:
                if not vals.get('helpdesk_area_id'):
                    raise ValidationError(_("Field helpdesk area is required with this department"))
        res = super(HelpdeskTicket, self).write(vals)

        if vals.get('stage_id'):

            global_stage = self.env['helpdesk.ticket.stage'].sudo().search(
                [('id', '=', vals['stage_id']), ('is_global', '=', True)],
                limit=1)
            if global_stage:
                for rec in self:
                    if rec.team_id.external:
                        created_user = rec.create_uid
                        created_employee = self.env['hr.employee'].sudo().search([('user_id', '=', created_user.id)])
                        created_employee_department = created_employee.department_id
                        created_employee_team = self.env['helpdesk.ticket.team'].search(
                            [('department_ids', 'in', created_employee_department.id)], limit=1)
                        rec.to_check_team_id = created_employee_team.id
                        if rec.to_check_team_id:
                            rec.team_id = rec.to_check_team_id.id
                            rec.user_id = rec.create_uid.id
                            # rec.to_check_team_id = rec.team_id.id
            close_stage = self.env['helpdesk.ticket.stage'].sudo().search(
                [('id', '=', vals['stage_id']), ('is_close', '=', True)],
                limit=1)
            if close_stage:
                for rec in self:
                    admin_user = self.env.ref('base.user_admin')
                    super_user = self.env.su
                    if not super_user:
                        if rec.env.user.id == rec.team_id.close_user_id.id or rec.env.user.id == rec.create_uid.id:
                            pass
                        else:
                            if rec.create_uid.id != admin_user.id:
                                if rec.employee_id:
                                    if rec.sudo().employee_id.user_id:
                                        if rec.sudo().employee_id.user_id.id != rec.env.user.id:
                                            if rec.sudo().employee_id.department_id.id != rec.env.user.department_id.id:
                                                raise ValidationError(
                                                    _("You Don't Have Access To Move To Closing Stage"))
                            if rec.create_uid.id == admin_user.id:
                                if not rec.employee_id:
                                    if rec.partner_id:
                                        if rec.partner_id.assigned_to_id:
                                            if rec.partner_id.assigned_to_id.id != rec.env.user.id:
                                                if rec.partner_id.assigned_to_id.department_id.id != rec.env.user.department_id.id:
                                                    raise ValidationError(
                                                        _("You Don't Have Access To Move To Closing Stage"))
                                if rec.employee_id:
                                    if rec.env.user.id != admin_user:
                                        if rec.sudo().employee_id.department_id.id != rec.env.user.department_id.id:
                                            raise ValidationError(_("You Don't Have Access To Move To Closing Stage"))

            reopen_stage = self.env['helpdesk.ticket.stage'].sudo().search(
                [('id', '=', vals['stage_id']), ('is_reopen', '=', True)],
                limit=1)
            if reopen_stage:
                for rec in self:
                    if rec.team_id.external:
                        rec.team_id = rec.last_team_id.id
        if vals.get('team_id'):
            helpdesk_team = self.env['helpdesk.ticket.team'].browse(vals['team_id'])
            if not helpdesk_team.external:
                raise ValidationError(_('You cannot change the internal ticket team. '))

        if vals.get('partner_id'):
            for line in self.message_follower_ids:
                if vals['partner_id'] == line.partner_id.id:
                    self.message_follower_ids = [(2, line.id)]

        self._patch_cr_records()
        return res


    def _patch_cr_records(self):
        for rec in self:
            all_records = rec.helpdesk_cr_ids | rec.work_item_ids
            for record in all_records:
                patch_vals = {}
                if rec.partner_id and record.partner_id != rec.partner_id:
                    patch_vals['partner_id'] = rec.partner_id.id
                if rec.project_id and record.project_id != rec.project_id:
                    patch_vals['project_id'] = rec.project_id.id
                if not record.ticket_id:
                    patch_vals['ticket_id'] = rec.id
                if patch_vals:
                    record.sudo().write(patch_vals)


    def edit_error(self):
        raise ValidationError(
            _(
                """ The user who created this record can modify it.
                    You can modify Helpdesk Team and Assigned to.
                """))

    def action_assign_to_me(self):
        self.ensure_one()
        if self.env.user not in self.user_ids:
            raise ValidationError(_('You cannot assign this ticket to yourself'))
        self.sudo().write({'user_id': self.env.user.id})

    partner_ticket_ids = fields.Many2many('helpdesk.ticket', compute='_compute_partner_ticket_count',
                                          string="Partner Tickets", compute_sudo=True)
    partner_ticket_count = fields.Integer('Number of other tickets from the same partner',
                                          compute='_compute_partner_ticket_count', compute_sudo=True)
    partner_open_ticket_count = fields.Integer('Number of other open tickets from the same partner',
                                               compute='_compute_partner_ticket_count', compute_sudo=True)

    @api.depends('partner_id')
    def _compute_partner_ticket_count(self):
        for ticket in self:
            if ticket.partner_id:
                tickets = self.sudo().search([('partner_id', '=', ticket.partner_id.id), ('id', '!=', ticket.id)])
                ticket.partner_ticket_ids = tickets
                ticket.partner_ticket_count = len(tickets)
                ticket.partner_open_ticket_count = len(tickets.filtered(lambda t: not t.closed))
            else:
                ticket.partner_ticket_ids = False
                ticket.partner_ticket_count = 0
                ticket.partner_open_ticket_count = 0

    partner_phone = fields.Char(string='Customer Phone', compute='_compute_partner_phone',
                                inverse="_inverse_partner_phone", store=True, readonly=False, compute_sudo=True)

    # Used to submit tickets from a contact form
    commercial_partner_id = fields.Many2one(related="partner_id.commercial_partner_id", related_sudo=True)

    def _compute_partner_phone(self):
        for ticket in self:
            ticket.partner_phone = ticket.sudo().partner_id.phone

    def _inverse_partner_phone(self):
        for ticket in self:
            if not ticket.sudo().partner_id.phone:
                ticket.sudo().partner_id.phone = ticket.sudo().partner_phone

    def action_recompute_team_members(self):
        for rec in self.search([]):
            rec.user_ids = False
            if rec.team_id.team_user_ids:
                rec.sudo().user_ids += rec.sudo().team_id.team_user_ids
            if rec.team_id.department_ids:
                for department in rec.sudo().team_id.department_ids:
                    member_ids = department.sudo().member_ids
                    for member_id in member_ids:
                        rec.user_ids += member_id.user_id
            if rec.team_id.assigned_user_id:
                rec.user_ids += rec.sudo().team_id.assigned_user_id
            rec.user_ids += self.sudo().env.user
            rec.user_ids += self.sudo().create_uid
