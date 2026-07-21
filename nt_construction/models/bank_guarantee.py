# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class BankGuarantee(models.Model):
    """خطابات الضمان — Bank Guarantees / Letters of Credit"""
    _name = 'bank.guarantee'
    _description = 'Bank Guarantee / Letter of Credit'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'expiry_date asc, id desc'

    name = fields.Char(default=lambda self: _('New'), readonly=True, copy=False)
    project_id = fields.Many2one(
        'project.project', string='Project',
        domain=[('is_construction_project', '=', True)], tracking=True,
    )
    tender_id = fields.Many2one(
        'tender.tender', string='Tender',
        tracking=True,
    )
    company_id = fields.Many2one(
        'res.company', string='Company',
        compute='_compute_company_id', store=True, readonly=False,
        help='مأخوذ من المشروع أو المناقصة أو الشركة الافتراضية',
    )

    @api.depends('project_id.company_id', 'tender_id.company_id')
    def _compute_company_id(self):
        for rec in self:
            rec.company_id = (
                rec.project_id.company_id
                or rec.tender_id.company_id
                or self.env.company
            )
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
    )

    guarantee_type = fields.Selection([
        ('bid_bond', 'Bid Bond / Initial Guarantee'),
        ('performance', 'Performance Bond'),
        ('advance_payment', 'Advance Payment Guarantee'),
        ('retention', 'Retention Bond'),
        ('other', 'Other'),
    ], string='Type', default='performance', required=True, tracking=True)

    bank_id = fields.Many2one('res.bank', string='Issuing Bank', required=True)
    bank_branch = fields.Char(string='Branch')
    beneficiary_id = fields.Many2one('res.partner', string='Beneficiary', required=True)

    amount = fields.Monetary(string='Amount', currency_field='currency_id', required=True)
    percentage = fields.Float(string='% of Contract', help='النسبة المئوية من قيمة العقد')

    issue_date = fields.Date(string='Issue Date', required=True, tracking=True)
    expiry_date = fields.Date(string='Expiry Date', required=True, tracking=True)
    claim_date = fields.Date(string='Claim Date', copy=False, tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('issued', 'Issued'),
        ('extended', 'Extended'),
        ('returned', 'Returned'),
        ('claimed', 'Claimed'),
        ('expired', 'Expired'),
    ], string='Status', default='draft', required=True, copy=False, tracking=True)

    reference_number = fields.Char(string='Bank Reference No.')
    notes = fields.Text(string='Notes')
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')

    _sql_constraints = [
        ('name_uniq', 'unique(name, company_id)', 'Guarantee reference must be unique per company!'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('bank.guarantee') or _('New')
        return super().create(vals_list)

    @api.constrains('tender_id', 'project_id')
    def _check_tender_or_project(self):
        for rec in self:
            if not rec.tender_id and not rec.project_id:
                raise UserError(_('Please link the guarantee to either a Tender or a Project.'))

    def action_issue(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Only draft guarantees can be issued.'))
        self.write({'state': 'issued'})

    def action_extend(self):
        for rec in self:
            if rec.state not in ('issued', 'extended'):
                raise UserError(_('Only issued guarantees can be extended.'))
        self.write({'state': 'extended'})

    def action_return(self):
        for rec in self:
            if rec.state not in ('issued', 'extended'):
                raise UserError(_('Only issued guarantees can be returned.'))
        self.write({'state': 'returned'})

    def action_claim(self):
        for rec in self:
            if rec.state not in ('issued', 'extended'):
                raise UserError(_('Only issued guarantees can be claimed.'))
        self.write({'state': 'claimed', 'claim_date': fields.Date.context_today(rec)})

    def action_expire(self):
        self.write({'state': 'expired'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})
