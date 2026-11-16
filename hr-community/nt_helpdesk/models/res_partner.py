""" Initialize Res Partner """

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, MissingError, ValidationError, UserError


class ResPartner(models.Model):
    """
        Inherit Res Partner:
         -
    """
    _inherit = 'res.partner'






    code = fields.Char(default='New', readonly=True)
    assigned_to_id = fields.Many2one('res.users')
    secondary_mail = fields.Char()
    allowed_users = fields.One2many('project.helpdesk.config', 'partner_id', string='Allowed users',groups='helpdesk_mgmt.group_helpdesk_user,nt_helpdesk.group_helpdesk_technical_user')
    helpdesk_team_id = fields.Many2one('helpdesk.ticket.team',groups='helpdesk_mgmt.group_helpdesk_user,nt_helpdesk.group_helpdesk_technical_user')
    email = fields.Char(string="Portal mail 1 ")
    is_company = fields.Boolean()
    ref = fields.Char(string="Ref",
                      # search='_search_customer_red'
                      )

    @api.depends('company_type')
    def _compute_is_company(self):
        """ Compute is_company value """
        for rec in self:
            if rec.company_type == 'company':
                rec.is_company = True

    @api.model
    def create(self, vals):
        if not vals.get('ref') or vals.get('ref') in ('New', '/'):
            ptype = vals.get('contact_type')
            if ptype and ptype != 'contact':
                vals['ref'] = self.env['ir.sequence'].next_by_code('crm.customer')
        return super().create(vals)


    @api.model
    def name_search(self, name, args=None, operator='like', limit=100):
        if name:
            # Directly search within 'ref' field using the provided 'name'
            recs = self.search([('ref', operator, name)] + (args or []), limit=limit)
            if not recs:
                # If no records are found in 'ref', optionally search in 'name' field as a fallback
                recs = self.search([('name', operator, name)] + (args or []), limit=limit)
            return recs.name_get()
        return super(ResPartner, self).name_search(name, args=args, operator=operator, limit=limit)

    def name_get(self):
        result = []
        for rec in self:
            if rec.ref:
                name = rec.name
            else:
                name = rec.name
            result.append((rec.id, name))
        return result
