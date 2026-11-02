from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    construction_project_id = fields.Many2one(
        'project.project', index='btree_not_null', copy=False,
        readonly=True, check_company=True)
    construction_move_kind = fields.Selection([
        ('certificate', 'Client Certificate'),
        ('advance', 'Advance Payment'),
        ('retention_release', 'Retention Release'),
        ('subcontract_certificate', 'Subcontractor Certificate'),
    ], string='Construction Document', copy=False, readonly=True)
