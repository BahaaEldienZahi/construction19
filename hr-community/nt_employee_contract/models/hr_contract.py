from odoo import models, fields, api
from odoo.addons.hr_fleet.models import employee
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta


class HrContract(models.Model):
    _inherit = 'hr.contract'
    # contract_end_date= field's.Date(related = 'employee_id.contract_end_date',store=True)
    date_end = fields.Date(related='employee_id.contract_end_date', store=True)
    journal_id = fields.Many2one(related='employee_id.journal_id', store=True)

    branch = fields.Char(related='employee_id.branch', store=True)
    bank = fields.Char(related='employee_id.bank', store=True)
    bank_account = fields.Char(related='employee_id.bank_account', store=True)
    bank_cash_journal = fields.Selection(related='employee_id.bank_cash_journal', store=True)
    department_id = fields.Many2one(related='employee_id.department_id', store=True,readonly=True)
    job_id = fields.Many2one(related='employee_id.job_id', store=True,readonly=True)
    parent_id = fields.Many2one(related = 'employee_id.parent_id',store =True,string = "Manager")
    fellowship_fund = fields.Boolean(related = 'employee_id.fellowship_fund')
    day_wage = fields.Float('Day Wage')
    hour_wage = fields.Float('Hour Wage')
    over_hour = fields.Monetary(compute='_compute_over_hour', store=True)
    basic_salary = fields.Float('Basic Salary', compute='compute_salary_details', store=True, readonly=False)
    allowance = fields.Float('Allowance', compute='compute_salary_details', store=True, readonly=False)
    major_allowance = fields.Float('Major Allowance', compute='compute_salary_details', store=True, readonly=False)
    kpi = fields.Float('KPI', compute='compute_salary_details', store=True, readonly=False)
    target = fields.Float('Target', compute='compute_salary_details', store=True, readonly=False)
    payroll_type = fields.Selection([('marketing_managers', 'Marketing & Managers'),
                                     ('employee', 'Employee')])


    @api.depends('hour_wage')
    def _compute_over_hour(self):
        for rec in self:
            rec.over_hour = rec.hour_wage * 2


    @api.depends('wage', 'payroll_type')
    def compute_salary_details(self):
        for rec in self:
            if rec.payroll_type == 'employee':
                rec.basic_salary = (rec.wage * 50) / 100
                rec.allowance = (rec.wage * 30) / 100
                rec.kpi = (rec.wage * 20) / 100
            elif rec.payroll_type == 'marketing_managers':
                rec.basic_salary = (rec.wage * 50) / 100
                rec.allowance = (rec.wage * 30) / 100
                rec.kpi = (rec.wage * 20) / 100


    # @api.depends('employee_id.contract_end_date')
    # def get_end_date(self):
    #     for rec in self:
    #         if rec.employee_id:
    #             rec.date_end = rec.employee_id.contract_end_date
    #         else:
    #             rec.date_end =None

    # def archive_contract_and_employee(self):
    #     today = fields.Date.today()
    #     archive_end_date = int(
    #         self.env['ir.config_parameter'].sudo().get_param('nt_employee_contract.archive_end_date'))
    #     if today.day == archive_end_date:
    #         contract_ids = self.search([('probation_date_end', '<=', today)])
    #         for contract_id in contract_ids:
    #             contract_id.employee_id.active = False
    #             contract_id.active = False

    def archive_contract_and_employee(self):
        today = fields.Date.today()
        archive_end_date = int(
            self.env['ir.config_parameter'].sudo().get_param('nt_employee_contract.archive_end_date'))
        day_of_previous_month = int(
            self.env['ir.config_parameter'].sudo().get_param('nt_employee_contract.day_of_previous_month'))
        month_margin = 1
        date_of_previous_month = fields.Date.to_string(
            (datetime.now() + relativedelta(months=-month_margin, day=day_of_previous_month)).date())
        date_new = datetime.strptime(date_of_previous_month, '%Y-%m-%d').date()
        if today.day == archive_end_date:
            contract_ids = self.search([('date_end', '<=', date_new), ('state', '=', 'open')])
            for contract_id in contract_ids:
                contract_id.employee_id.active = False
                contract_id.active = False
