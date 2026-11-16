from odoo import models, fields, api

from odoo.exceptions import ValidationError


class ClearanceRequestLine(models.Model):
    _name = 'clearance.request.line'
    _description = 'Clearance Request Line'
    _order = 'sequence, id'

    request_id = fields.Many2one('clearance.request', required=True, ondelete='cascade', index=True)
    setup_id = fields.Many2one('clearance.setup', string="Section", required=True, index=True, ondelete='cascade')

    # Department from setup - stored and indexed for filtering
    department_id = fields.Many2one(
        'hr.department',
        related='setup_id.department_id',
        readonly=True,
        store=True,
        index=True  # Add index for better performance
    )

    name = fields.Char(string="Item", required=True)
    owner_ids = fields.Many2many('res.users', string="Owners")
    sequence = fields.Integer(default=10)
    not_done = fields.Boolean(string="Yes", default=False)
    is_done = fields.Boolean(string="No", default=False)
    note = fields.Char(string="Note")
    is_locked = fields.Boolean(compute="_compute_is_locked", store=False)
    request_state = fields.Selection(related="request_id.state", store=False, readonly=True)
    selected = fields.Boolean(string="Select", default=False)

    @api.depends(
        'request_id.line_ids.is_done',
        'request_id.line_ids.setup_id',
        'request_id.line_ids.setup_id.sequence',
        'setup_id.sequence',
        'request_id'
    )
    def _compute_is_locked(self):
        # Batch compute per request
        req_to_pending_seq = {}

        # جمع requests
        requests = self.mapped('request_id')
        for req in requests:
            # نحدد أول setup (sequence) فيه أي line مش done
            pending_lines = req.line_ids.filtered(lambda l: not l.is_done)
            if not pending_lines:
                req_to_pending_seq[req.id] = None  # كله مفتوح
                continue

            pending_seq = min(pending_lines.mapped('setup_id.sequence') or [None])
            req_to_pending_seq[req.id] = pending_seq

        for line in self:
            pending_seq = req_to_pending_seq.get(line.request_id.id)
            if pending_seq is None:
                line.is_locked = False
            else:
                # مقفول لو section بتاعه بعد أول section ناقص
                line.is_locked = (line.setup_id.sequence > pending_seq)

        # ✅ Server-side protection (important)
    def write(self, vals):
        if any(k in vals for k in ('is_done', 'note')):
            locked = self.filtered('is_locked')
            if locked:
                raise ValidationError(("لا يمكن تعديل هذا القسم قبل إكمال الأقسام السابقة."))
        return super().write(vals)