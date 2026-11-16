# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, time
from pytz import timezone, UTC

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
# from odoo.addons.resource.models.utils import HOURS_PER_DAY


class HrLeave(models.Model):
    _inherit = 'hr.leave'
    is_mission = fields.Boolean(string='Mission', compute='_compute_mission_type', store=True)

    def _calc_leave(self):
        """ Calc Leave """
        leave_visibility_ids = self.env['hr.leave.type'].search(
            [('visibility', '=', True)])
        visibility_ids = []
        if leave_visibility_ids:
            for rec in leave_visibility_ids:
                allocation_ids = self.env['hr.leave.allocation'].search(
                    [('employee_id', '=', self.employee_id.id),
                     ('holiday_status_id', 'in',
                      rec.leave_type_ids.ids)])
                if allocation_ids:
                    days = sum(
                        alloc.holiday_status_id.virtual_remaining_leaves for
                        alloc in
                        allocation_ids)
                    if days == 0:
                        visibility_ids.append(rec.id)

        if visibility_ids:
            records = self.env['hr.leave.type'].search(
                [('visibility', '=', False)])
            if records:
                return ['|', ('id', 'in', visibility_ids),
                        ('id', 'in', records.ids)]
            else:
                return [('id', 'in', visibility_ids)]
        else:
            return [('visibility', '=', False)]

    holiday_status_id = fields.Many2one(
        domain=_calc_leave
    )
    attachment = fields.Binary()
    required_attachment = fields.Boolean(
        related='holiday_status_id.required_attachment')
    mission = fields.Boolean(related='holiday_status_id.mission')
    partner_id = fields.Many2one(
        'res.partner', string="Customer", domain="[('contact_type','in',['customer','both'])]",
    )
    project_id = fields.Many2one(
        'project.project', domain="[('partner_id', '=', partner_id)]"
    )

    @api.constrains('number_of_days')
    def _check_all_days(self):
        """ Validate all_days """
        for rec in self:
            if rec.holiday_status_id.all_days and rec.number_of_days < rec.holiday_status_id.virtual_remaining_leaves:
                raise ValidationError(_(
                    "You must take " + str(
                        rec.holiday_status_id.virtual_remaining_leaves) + "Day"))

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """ partner_id """
        self.project_id = False

    @api.depends('holiday_status_id')
    def _compute_mission_type(self):
        for rec in self:
            rec.is_mission = False
            if rec.holiday_status_id:
                if rec.holiday_status_id.mission:
                    rec.is_mission = True



    @api.constrains('holiday_status_id', )
    def _check_time_off_type_permission(self):
        for rec in self:

            first_date = datetime(rec.request_date_from.year, rec.request_date_from.month, 1).strftime("%Y-%m-%d")
            if rec.request_date_from.month + 1 <= 12:
                last_date = (datetime(rec.request_date_from.year, rec.request_date_from.month + 1, 1) + timedelta(
                days=-1)).strftime("%Y-%m-%d")
            else:
                last_date = (datetime(rec.request_date_from.year +1, 1, 1) + timedelta(days=-1)).strftime("%Y-%m-%d")
            if rec.holiday_status_id:
                if rec.holiday_status_id.is_permission:
                    limited_hours = rec.holiday_status_id.permission_hours
                    previous_permissions = self.env['hr.leave'].search([
                        ('employee_id', '=', rec.employee_id.id),
                        ('id', '!=', rec.id),
                        ('request_date_from', '>=', first_date),
                        ('request_date_from', '<=', last_date),
                    ]).filtered(
                        lambda permission: permission.holiday_status_id.is_permission).mapped("number_of_hours_display")
                    permissions = self.env['hr.leave'].search([
                        ('employee_id', '=', rec.employee_id.id),
                        ('request_date_from', '>=', first_date),
                        ('request_date_from', '<=', last_date),
                    ]).filtered(
                        lambda permission: permission.holiday_status_id.is_permission).mapped("number_of_hours_display")

                    if permissions:
                        if sum(permissions) > limited_hours or sum(permissions) > limited_hours:
                            raise ValidationError(
                                _('You are not allowed to request more than {} h/month, and the remaining balance will be {}.'.format(
                                    limited_hours, limited_hours - sum(previous_permissions),
                                )))



