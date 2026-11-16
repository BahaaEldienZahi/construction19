""" Initialize Hr Employee """
from odoo import api, fields, models
from lxml import etree


class HrEmployee(models.Model):
    """
        Inherit Hr Employee:
         -
    """
    _inherit = 'hr.employee'

    last_attendance_id = fields.Many2one(
        'hr.attendance', compute='_compute_last_attendance_id', store=True,
        groups="hr_attendance.group_hr_attendance_officer,hr.group_hr_user,base.group_user")
    signature=fields.Binary(string='Signature')
    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        def make_delegated_fields_no_create(node):
            for child in node.iterchildren():
                if child.tag == 'field':
                    child.set('options', "{'no_open': 'True'}")
                    pass
                else:
                    make_delegated_fields_no_create(child)
            return node

        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == 'form':
            arch = make_delegated_fields_no_create(arch)
        return arch, view

    def _get_timesheet_manager_id_domain(self):
        group_team_leader = self.env.ref('national_employee.team_leader_for_timesheet_group')
        group_admin = self.env.ref('hr_timesheet.group_hr_timesheet_approver')
        if group_team_leader and group_admin:
            domain = [('groups_id', 'in', [group_admin.id, group_team_leader.id])]
        elif group_team_leader:
            domain = [('groups_id', 'in', [group_team_leader.id])]
        elif group_admin:
            domain = [('groups_id', 'in', [group_admin.id])]
        else:
            domain = []
        return domain

    current_leave_id = fields.Many2one('hr.leave.type', compute='_compute_current_leave',
                                       string="Current Time Off Type",
                                       groups="hr.group_hr_user,national_employee.employee_user_group")
    message_main_attachment_id = fields.Many2one(groups="hr.group_hr_user,national_employee.employee_user_group")

    timesheet_manager_id = fields.Many2one(
        'res.users', string='Timesheet',
        domain=_get_timesheet_manager_id_domain,
        help='Select the user responsible for approving "Timesheet" of this employee.\n'
             'If empty, the approval is done by a Timesheets > Administrator or a Timesheets > User: all timesheets (as determined in the users settings).')

    name_in_arabic = fields.Char()
    ref_employee_id = fields.Many2one(
        'hr.employee', string='Referral By Employee'
    )
    referral_by_email = fields.Char()
    hiring_date = fields.Date()
    social_insurance_number = fields.Char()
    medical_insurance_id = fields.Char(string='Medical Insurance Id')
    medical_staff_id = fields.Char(string='Medical Staff Id')
    identification_id_expiry_date = fields.Date()
    military_certificate_expiry_date = fields.Date()
    bank_cash_journal = fields.Selection([('bank', 'Bank'), ('cash', 'Cash')], string='Journal Type')
    journal_id = fields.Many2one('account.journal', string='Journal', compute='_compute_journal_id')
    branch = fields.Char(string='Branch')
    bank = fields.Char(string='Bank ID')
    bank_account = fields.Char(string='Bank Account')
    address_book_id = fields.Many2one('address.book')

    def _compute_current_leave(self):
        self.current_leave_id = False

        holidays = self.env['hr.leave'].sudo().search([
            ('employee_id', 'in', self.ids),
            ('date_from', '<=', fields.Datetime.now()),
            ('date_to', '>=', fields.Datetime.now()),
            ('state', '=', 'validate'),
        ])
        for holiday in holidays:
            employee = self.filtered(lambda e: e.id == holiday.employee_id.id)
            employee.current_leave_id = holiday.holiday_status_id.id

    @api.depends('bank_cash_journal')
    def _compute_journal_id(self):
        for rec in self:
            rec.journal_id = False
            if rec.bank_cash_journal == 'bank':
                bank_journal = self.env['ir.config_parameter'].sudo().get_param('national_employee.bank_journal')
                if bank_journal:
                    rec.journal_id = int(bank_journal)
            elif rec.bank_cash_journal == 'cash':
                cash_journal = self.env['ir.config_parameter'].sudo().get_param('national_employee.cash_journal')
                if cash_journal:
                    rec.journal_id = int(cash_journal)

    @api.model_create_multi
    def create(self, vals_list):
        """
            Override create method
             - sequence name
        """
        for vals in vals_list:
            sequence = self.env['ir.sequence'].next_by_code(
                'employee.barcode') or ''
            vals.update(barcode=sequence)
            res = super(HrEmployee, self).create(vals)
            # for emp in res:
            #     address_book_id = self.env['address.book'].sudo().create({
            #         'name': emp.name,
            #         'mobile_phone': emp.mobile_phone,
            #         'work_email': emp.work_email,
            #         'department_id': emp.department_id.id,
            #         'job_id': emp.job_id.id,
            #         'parent_id': emp.parent_id.id,
            #     })
            #     vals['address_book_id'] = address_book_id.id
            return res

    # def write(self, vals):
    #     res = super(HrEmployee, self).write(vals)
    #     address_book = self.env['address.book']
    #     address_book_id = address_book.search([('id', '=', self.address_book_id.id)])
    #     for rec in self:
    #         if rec.name:
    #             address_book_id.write({'name': rec.name})
    #
    #         if rec.mobile_phone:
    #             address_book_id.write({'mobile_phone': rec.mobile_phone})
    #
    #         if rec.work_email:
    #             address_book_id.write({'work_email': rec.work_email})
    #
    #         if rec.department_id:
    #             address_book_id.write({'department_id': rec.department_id})
    #
    #         if rec.job_id:
    #             address_book_id.write({'job_id': rec.job_id})
    #
    #         if rec.parent_id:
    #             address_book_id.write({'parent_id': rec.parent_id})
    #
    #     return res
    def cron_export_all_employees_to_address_book(self):
        # delete all records in address book before run
        self.env['address.book'].search([]).unlink()
        emps = self.env['hr.employee'].search([('active', '=', True)])
        book = self.env['address.book'].sudo()
        for emp in emps:
            address_book_id = book.create({
                'name': emp.name,
                'mobile_phone': emp.mobile_phone,
                'work_email': emp.work_email,
                'department_id': emp.department_id.id,
                'job_id': emp.job_id.id,
                'parent_id': emp.parent_id.id,
            })
            emp.write({
                'address_book_id': address_book_id
            })

    def action_export_emps_to_address_book(self):
        address_books = self.env['address.book'].sudo().search([]).mapped('id')
        book = self.env['address.book'].sudo()
        for emp in self:
            if emp.address_book_id.id in address_books:
                book_id = book.browse(emp.address_book_id.id)
                book_id.write({
                    'name': emp.name,
                    'mobile_phone': emp.mobile_phone,
                    'work_email': emp.work_email,
                    'department_id': emp.department_id.id,
                    'job_id': emp.job_id.id,
                    'parent_id': emp.parent_id.id,
                })
            else:
                address_book_id = book.create({
                    'name': emp.name,
                    'mobile_phone': emp.mobile_phone,
                    'work_email': emp.work_email,
                    'department_id': emp.department_id.id,
                    'job_id': emp.job_id.id,
                    'parent_id': emp.parent_id.id,
                })
                emp.write({'address_book_id': address_book_id.id})


class HrEmployeePublic(models.Model):
    """
        Inherit Hr Employee Public:
         -
    """
    _inherit = 'hr.employee.public'

    name_in_arabic = fields.Char()
    ref_employee_id = fields.Char()
    referral_by_email = fields.Char()
    hiring_date = fields.Date()
    social_insurance_number = fields.Char()
    medical_insurance_id = fields.Char(string='Medical Insurance Id')
    medical_staff_id = fields.Char(string='Medical Staff Id')
    identification_id_expiry_date = fields.Date()
    military_certificate_expiry_date = fields.Date()
    bank_cash_journal = fields.Selection([('bank', 'Bank'), ('cash', 'Cash')], string='Journal Type')
    journal_id = fields.Many2one('account.journal', string='Journal', compute='_compute_journal_id')

    @api.depends('bank_cash_journal')
    def _compute_journal_id(self):
        for rec in self:
            rec.journal_id = False
            if rec.bank_cash_journal == 'bank':
                bank_journal = self.env['ir.config_parameter'].sudo().get_param('national_employee.bank_journal')
                if bank_journal:
                    rec.journal_id = int(bank_journal)
            elif rec.bank_cash_journal == 'cash':
                cash_journal = self.env['ir.config_parameter'].sudo().get_param('national_employee.cash_journal')
                if cash_journal:
                    rec.journal_id = int(cash_journal)

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        def make_delegated_fields_no_create(node):
            for child in node.iterchildren():

                if child.tag == 'field':
                    child.set('options', "{'no_open': 'True'}")
                    pass
                else:
                    make_delegated_fields_no_create(child)
            return node

        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == 'form':
            arch = make_delegated_fields_no_create(arch)
        return arch, view


class HrDepartment(models.Model):
    """
        Inherit Hr Department:
         -
    """
    _inherit = 'hr.department'

    apply_flexible_hour = fields.Boolean()
