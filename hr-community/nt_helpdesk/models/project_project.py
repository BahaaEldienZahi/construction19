# -*- coding: utf-8 -*-
import json

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError



class ProjectProject(models.Model):
    _inherit = 'project.project'

    assigned_to_id = fields.Many2one('res.users', string='Assigned To')
    helpdesk_team_id = fields.Many2one('helpdesk.ticket.team', string='Team')
    allowed_users = fields.One2many('project.helpdesk.config', 'project_id', string='Allowed users')

    code = fields.Char(readonly=1)


    def reset_code_sequence_to_old_records(self):
        for rec in self:
            # rec.code = ""
            rec.code = self.env['ir.sequence'].next_by_code(
                'project.project')

    # @api.constrains('code')
    # def unique_code(self):
    #     for rec in self:
    #         project_obj = self.env['project.project'].search_count([('code', '=', rec.code)])
    #         print(project_obj)
    #         if project_obj >= 2:
    #             raise ValidationError("Code must be Unique")

    @api.model
    def create(self, vals):
        """
            Override create method
             - sequence name
        """
        if vals.get('code', 'New') == 'New':
            vals['code'] = self.env['ir.sequence'].next_by_code(
                'project.project') or '/'
        return super(ProjectProject, self).create(vals)

    @api.model
    def name_search(self, name, args=None, operator='=like', limit=100):
        if name:
            recs = self.search(
                ['|', ('name', operator, name), ('code', operator, name)] + (
                        args or []), limit=limit)
            return recs.name_get()
        return super(ProjectProject, self).name_search(name, args=args,
                                                       operator=operator,
                                                       limit=limit)

    def name_get(self):
        result = []
        for rec in self:
            name = rec.code + ' ' + rec.name
            result.append((rec.id, name))
        return result

    def copy(self, default=None):
        self.ensure_one()
        default = default or {}
        if 'code' not in default:
            default['code'] = self.env['ir.sequence'].next_by_code(
                'project.project') or '/'
        res = super(ProjectProject,self).copy(default)
        return res

class ProjectHelpdeskConfig(models.Model):
    _name = 'project.helpdesk.config'

    @api.model
    def _getUserGroupId(self):
        return [('groups_id', '=', self.env.ref('base.group_portal').id), ('customer_user_portal', '=', True)]

    project_id = fields.Many2one('project.project')
    partner_id = fields.Many2one('res.partner',
                                 groups='helpdesk_mgmt.group_helpdesk_user,nt_helpdesk.group_helpdesk_technical_user')

    user_id = fields.Many2one('res.users', string='Customer', domain=_getUserGroupId, required=True)
    team_id = fields.Many2one('helpdesk.ticket.team', string='Team', )
    team_domain = fields.Binary('team domain', compute='compute_team_domain')

    @api.onchange('team_id')
    def onchange_team_id(self):
        if self.assigned_to:
            self.assigned_to = False

    user_ids = fields.Many2many('res.users',
                                'res_users_project_helpdesk_config_rel',
                                'user_id', 'project_helpdesk_config_id',
                                'Related Team Users',
                                compute='compute_related_user_ids_from_team', )

    @api.depends('user_id', 'team_id')
    def compute_team_domain(self):
        for rec in self:

            prev_teams_ids = self.env['project.helpdesk.config'].search(
                [('partner_id', '=', rec.partner_id._origin.id), ('user_id', '=', rec.user_id._origin.id)]).mapped(
                'team_id').ids
            if prev_teams_ids:
                rec.team_domain = [('id', 'not in', prev_teams_ids)]
            else:
                rec.team_domain = [(1, '=', 1)]

    @api.depends('team_id', 'team_id.department_ids', 'team_id.team_user_ids', 'team_id.assigned_user_id')
    def compute_related_user_ids_from_team(self):
        for rec in self:
            rec.user_ids = False
            if rec.team_id.team_user_ids:
                rec.sudo().user_ids += rec.team_id.team_user_ids
            if rec.team_id.department_ids:
                for department in rec.sudo().team_id.department_ids:
                    member_ids = department.sudo().member_ids
                    for member_id in member_ids:
                        rec.user_ids += member_id.user_id
            if rec.team_id.assigned_user_id:
                rec.user_ids += rec.sudo().team_id.assigned_user_id

    assigned_to = fields.Many2one('res.users', string='Assigned To',
                                  domain="[('id', 'in', user_ids)]")
    email = fields.Char(string="Portal mail ", related='user_id.login', )
    view_all_tickets = fields.Boolean('View All Tickets')

