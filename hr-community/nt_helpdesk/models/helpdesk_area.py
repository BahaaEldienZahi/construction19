from odoo import api, fields, models


class HelpdeskArea(models.Model):

    _name = 'helpdesk.area'
    _description = 'Helpdesk Area'

    name = fields.Char(required=True)
    parent_id = fields.Many2one(comodel_name="helpdesk.area", string="Parent Area", )



