# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ConstructionApprovalMixin(models.AbstractModel):
    """Reusable two-level approval workflow.
    Concrete models must also inherit ['mail.thread', 'mail.activity.mixin']
    and may override `_on_final_approval` to trigger side-effects."""
    _name = 'construction.approval.mixin'
    _description = 'Two-level Approval Workflow Mixin'

    # Subclasses may override these xmlids if they need different approver groups
    _approval_group_l1_xmlid = 'nt_construction.group_construction_approver_l1'
    _approval_group_l2_xmlid = 'nt_construction.group_construction_approver_l2'

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved_l1', 'Approved (Level 1)'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ], default='draft', required=True, copy=False, tracking=True)

    approver_l1_id = fields.Many2one('res.users', string='Approved By (L1)', readonly=True, copy=False)
    approval_l1_date = fields.Datetime(string='L1 Approval Date', readonly=True, copy=False)
    approver_l2_id = fields.Many2one('res.users', string='Approved By (L2)', readonly=True, copy=False)
    approval_l2_date = fields.Datetime(string='L2 Approval Date', readonly=True, copy=False)
    rejection_reason = fields.Text(copy=False)

    def action_submit_for_approval(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Only draft records can be submitted for approval.'))
        self.write({'state': 'submitted'})

    def action_approve_l1(self):
        if not self.env.user.has_group(self._approval_group_l1_xmlid):
            raise UserError(_('You are not authorized to give Level 1 approval.'))
        for rec in self:
            if rec.state != 'submitted':
                raise UserError(_('Record must be submitted before Level 1 approval.'))
        self.write({
            'state': 'approved_l1',
            'approver_l1_id': self.env.user.id,
            'approval_l1_date': fields.Datetime.now(),
        })

    def action_approve_l2(self):
        if not self.env.user.has_group(self._approval_group_l2_xmlid):
            raise UserError(_('You are not authorized to give Level 2 (final) approval.'))
        for rec in self:
            if rec.state != 'approved_l1':
                raise UserError(_('Record must have Level 1 approval before final approval.'))
        self.write({
            'state': 'approved',
            'approver_l2_id': self.env.user.id,
            'approval_l2_date': fields.Datetime.now(),
        })
        self._on_final_approval()

    def action_reject(self):
        for rec in self:
            if rec.state not in ('submitted', 'approved_l1'):
                raise UserError(_('Only submitted or L1-approved records can be rejected.'))
        self.write({'state': 'rejected'})

    def action_reset_draft(self):
        self.write({
            'state': 'draft',
            'approver_l1_id': False,
            'approval_l1_date': False,
            'approver_l2_id': False,
            'approval_l2_date': False,
            'rejection_reason': False,
        })

    def action_cancel(self):
        for rec in self:
            if rec.state == 'approved':
                raise UserError(_('An approved record cannot be cancelled directly. Reverse its effects manually first.'))
        self.write({'state': 'cancelled'})

    def _on_final_approval(self):
        """Hook for subclasses — called once, right after state becomes 'approved'."""
        pass