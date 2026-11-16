""" Initialize Helpdesk Team """

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class HelpdeskTeam(models.Model):
    """
        Inherit Helpdesk Team:
         -
    """
    _inherit = 'helpdesk.ticket.team'

    assigned_user_id = fields.Many2one(
        'res.users',
        string='Automatic Assigned User To Ticket'

    )
    helpdesk_area_ids = fields.Many2many('helpdesk.area', string='Areas')
    helpdesk_categ_ids = fields.Many2many('helpdesk.category', string='Category')
    helpdesk_product_ids = fields.Many2many('product.template', string='Products',
                                            domain="[('helpdesk_category_id', 'in', helpdesk_categ_ids)]")
    helpdesk_ticket_type_ids = fields.Many2many('helpdesk.ticket.type', string='Tickets Type')
    department_ids = fields.Many2many(comodel_name="hr.department", string="Department", store=True)
    team_user_ids = fields.Many2many(comodel_name="res.users", relation="team_user_ids", string="Users", store=True)
    assign_user_ids = fields.Many2many(comodel_name="res.users", relation="assign_user_ids", string="TL Assign",
                                       store=True)
    close_user_id = fields.Many2one(comodel_name="res.users", string="Close Ticket")
    area = fields.Boolean(string="Area")
    external = fields.Boolean(string="External")
    invisible_field_ids = fields.Many2many(comodel_name="ir.model.fields", string="Invisible Fields",
                                           relation="invisible_field_ids",
                                           domain=[('model_id.model', '=', 'helpdesk.ticket'),
                                                   ('name', 'in', ['helpdesk_area_id', 'category_id', 'tag_ids',
                                                                   'ticket_type_id', 'helpdesk_product_id',
                                                                   'any_desk_id', 'recurred_issue', 'cr_number',
                                                                   'partner_id', 'customer_code', 'email_cc',
                                                                   'partner_phone', 'project_code', 'user_id',
                                                                   'priority', 'description_html', 'support_log']
                                                    ), ])
    required_field_ids = fields.Many2many(comodel_name="ir.model.fields", column1="",
                                          column2="", string="Required Fields",
                                          domain=[('model_id.model', '=', 'helpdesk.ticket'),
                                                  ('name', 'in', ['helpdesk_area_id', 'category_id', 'tag_ids',
                                                                  'ticket_type_id', 'helpdesk_product_id',
                                                                  'any_desk_id', 'recurred_issue', 'cr_number',
                                                                  'partner_id', 'customer_code', 'email_cc',
                                                                  'partner_phone', 'project_code', 'user_id',
                                                                  'priority', 'description_html', 'support_log']
                                                   ), ])
    is_team_project = fields.Boolean(string="Team Project")

    required_project_team_id = fields.Boolean(string="Required Project for team", )
    required_stage_id = fields.Many2one('helpdesk.ticket.stage', domain="[('team_ids', 'in', [id])]",
                                        string="Required Stage", )

    helpdesk_required_field_ids = fields.Many2many(comodel_name="ir.model.fields", relation="helpdesk_team_helpdesk_required_fields_rel", column1="team_id", column2="field_id", string="Helpdesk Required Fields",
                                          domain=[('model_id.model', '=', 'helpdesk.ticket'), ('name', 'in', ['helpdesk_cr_ids', 'project_id', 'work_item_ids'])])

    @api.onchange('area', 'invisible_field_ids')
    def check_area(self):
        for rec in self:
            helpdesk_area_id = self.env['ir.model.fields'].search(
                [('model_id.model', '=', 'helpdesk.ticket'), ('name', '=', 'helpdesk_area_id')], limit=1)
            if rec.area and helpdesk_area_id.name in rec.invisible_field_ids.mapped('name'):
                raise ValidationError(_("Can't make field invisible with required Helpdesk Area "))

    # @api.constrains('invisible_field_ids', 'required_field_ids')
    # def check_invisible_field_ids(self):
    #     for rec in self:
    #         if rec.required_field_ids in rec.invisible_field_ids:
    #             raise ValidationError("Can't make field required with invisible ")
    #         if rec.invisible_field_ids in rec.required_field_ids:
    #             raise ValidationError("Can't make field invisible with required ")

    @api.onchange('department_ids', 'team_user_ids')
    def team_record_rule_clear_cache(self):
        self.env.registry.clear_cache()
