from odoo import api, fields, models


class AddressBook(models.Model):
    _name = 'address.book'
    _description = 'Address book for employees'

    name = fields.Char('Employee Name', readonly=True, required=True)
    mobile_phone = fields.Char('Work Mobile', readonly=True)
    work_email = fields.Char('Work Email', readonly=True)
    department_id = fields.Many2one('hr.department', readonly=True)
    job_id = fields.Many2one('hr.job', readonly=True)
    parent_id = fields.Many2one('hr.employee', readonly=True)