from odoo import api, models
from odoo.exceptions import AccessError, UserError

# Context marker set only by server-side workflow methods. It is a Python object, so it can
# never be sent from a JSON-RPC client (a client-supplied context key would be a bypass).
_WORKFLOW_TOKEN = object()


class ConstructionWorkflowGuard(models.AbstractModel):
    """Workflow fields (state, approver stamps, links to accounting documents) can only be
    changed by the document's own action methods, never by a direct write/create/import.

    Concrete models list their protected fields in ``_workflow_guarded_fields`` and change
    them through ``self._workflow_write(vals)``.
    """
    _name = 'construction.workflow.guard'
    _description = 'Construction Workflow Field Guard'

    _workflow_guarded_fields = ('state',)

    def _as_workflow(self):
        """Same records, allowed to change guarded/locked fields (server-side code only)."""
        return self.with_context(construction_workflow=_WORKFLOW_TOKEN)

    def _workflow_write(self, vals):
        return self._as_workflow().write(vals)

    def _check_construction_role(self, *group_xmlids):
        """Raise unless the user holds one of the roles. Project administrators
        (``project.group_project_manager``) act as construction admins and always pass."""
        user = self.env.user
        if self.env.su or user.has_group('project.group_project_manager'):
            return
        if not any(user.has_group(xmlid) for xmlid in group_xmlids):
            names = [self.env.ref(xmlid).name for xmlid in group_xmlids]
            raise UserError(self.env._(
                'This action is reserved to: %(roles)s.', roles=', '.join(names)))

    def _is_workflow_context(self):
        return self.env.context.get('construction_workflow') is _WORKFLOW_TOKEN

    def _raise_guarded(self, field_names):
        raise AccessError(self.env._(
            'The fields %(fields)s of %(model)s can only be changed with the workflow buttons.',
            fields=', '.join(sorted(field_names)), model=self._description,
        ))

    @api.model_create_multi
    def create(self, vals_list):
        if not self._is_workflow_context():
            defaults = self.default_get(list(self._workflow_guarded_fields))
            for vals in vals_list:
                forced = {
                    fname for fname in self._workflow_guarded_fields
                    if fname in vals and vals[fname] != defaults.get(fname, False)
                    and vals[fname] not in (False, None)
                }
                if forced:
                    self._raise_guarded(forced)
        return super().create(vals_list)

    def write(self, vals):
        if not self._is_workflow_context():
            guarded = set(vals) & set(self._workflow_guarded_fields)
            if guarded:
                self._raise_guarded(guarded)
        return super().write(vals)


class ConstructionLockedAfterSubmit(models.AbstractModel):
    """Approval documents are frozen once submitted: their content can only change again
    after a reject/reset back to draft. Line models call ``_check_parent_editable``."""
    _name = 'construction.locked.after.submit'
    _description = 'Construction Document Locked After Submission'

    _editable_states = ('draft',)
    # fields that stay editable in any state (free text, chatter-related)
    _always_editable_fields = (
        'rejection_reason', 'message_follower_ids', 'activity_ids', 'message_main_attachment_id',
    )

    def _check_editable(self, field_names=None):
        if self.env.context.get('construction_workflow') is _WORKFLOW_TOKEN:
            return
        if field_names is not None and not (set(field_names) - set(self._always_editable_fields)):
            return
        locked = self.filtered(lambda rec: rec.state not in self._editable_states)
        if locked:
            raise UserError(self.env._(
                '%(docs)s is no longer in draft and cannot be modified. '
                'Reject it or reset it to draft first.',
                docs=', '.join(locked.mapped('display_name')),
            ))

    def write(self, vals):
        self._check_editable(vals.keys())
        return super().write(vals)

    def unlink(self):
        self._check_editable()
        return super().unlink()


class ConstructionLockedLine(models.AbstractModel):
    """Lines of a document using ``construction.locked.after.submit``: creating, editing or
    deleting a line is refused when the parent document is locked."""
    _name = 'construction.locked.line'
    _description = 'Construction Document Line Locked With Its Parent'

    _locked_parent_field = None  # e.g. 'certificate_id'

    def _check_parent_editable(self, parents=None):
        if parents is None:
            parents = self[self._locked_parent_field]
        parents._check_editable()

    @api.model_create_multi
    def create(self, vals_list):
        parent_model = self.env[self._fields[self._locked_parent_field].comodel_name]
        parent_ids = {vals.get(self._locked_parent_field) for vals in vals_list} - {False, None}
        self._check_parent_editable(parent_model.browse(parent_ids))
        return super().create(vals_list)

    def write(self, vals):
        self._check_parent_editable()
        if vals.get(self._locked_parent_field):
            parent_model = self.env[self._fields[self._locked_parent_field].comodel_name]
            self._check_parent_editable(parent_model.browse(vals[self._locked_parent_field]))
        return super().write(vals)

    def unlink(self):
        self._check_parent_editable()
        return super().unlink()
