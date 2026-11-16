from odoo import models, fields, api, SUPERUSER_ID, _
from lxml import etree
import logging
from odoo.exceptions import ValidationError
_logger = logging.getLogger(__name__)


class ClearanceRequest(models.Model):
    _name = 'clearance.request'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = 'Employee Clearance Request'
    _order = 'id desc'
    _rec_name = 'name'

    name = fields.Char(string="Employee Clearance Request Name", default='Clearance Request')
    resignation_id = fields.Many2one('hr.resignation', required=True, ondelete='cascade', index=True)
    employee_id = fields.Many2one('hr.employee', related='resignation_id.employee_id', store=True, readonly=True)
    department_id = fields.Many2one('hr.department', related='resignation_id.department_id', store=True, readonly=True)
    resignation_date = fields.Date(related='resignation_id.resignation_date', store=True, readonly=True)
    end_of_notice_period = fields.Date(related='resignation_id.end_notice_period', store=True, readonly=True)
    last_working_day = fields.Date(related='resignation_id.last_working_day', store=True, readonly=True)
    has_selected_lines = fields.Boolean(compute='_compute_has_selected_lines', store=False)
    has_done_lines = fields.Boolean(compute='_compute_done_lines', store=False)

    line_ids = fields.One2many('clearance.request.line', 'request_id', ondelete='cascade')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
    ], default='draft', string="Status", tracking=True)

    # -------------------------
    # Dynamic dept fields build
    # -------------------------
    @api.model
    def _register_hook(self):
        res = super()._register_hook()
        self._build_department_line_fields()
        return res

    @api.model
    def _build_department_line_fields(self):
        """
        Build one2many fields per department to avoid Odoo UI caching issue
        when repeating the same one2many field (line_ids) in multiple notebook pages.
        """
        env = api.Environment(self._cr, SUPERUSER_ID, {})
        setups = env['clearance.setup'].search([])
        depts = setups.mapped('department_id')

        for dept in depts:
            fname = f"x_line_ids_dept_{dept.id}"
            if fname in self._fields:
                continue

            field = fields.One2many(
                'clearance.request.line',
                'request_id',
                string=dept.name,
                domain=[('department_id', '=', dept.id)],
            )
            self._add_field(fname, field)

    # -------------------------
    # Dynamic view helpers
    # -------------------------
    def _get_base_form_view(self):
        return self.env.ref("nt_clearance.view_clearance_request_form", raise_if_not_found=False)

    def _get_dynamic_view_identity(self):
        inherit_view_name = "clearance_request_dyn_notebook"
        key = "nt_clearance.clearance_request_dyn_notebook"
        return inherit_view_name, None, None, key

    def _remove_dynamic_view(self):
        _, _, _, key = self._get_dynamic_view_identity()
        views = self.env['ir.ui.view'].sudo().search([
            ('key', '=', key),
            ('model', '=', self._name),
            ('type', '=', 'form'),
        ])
        if views:
            views.unlink()

    def _clear_view_caches(self):
        self.env.registry.clear_cache()
        self.env['ir.ui.view'].invalidate_model(['arch_db'])
        self.env.invalidate_all()

    def _ensure_dynamic_view(self):
        base_view = self._get_base_form_view()
        setups = self.env['clearance.setup'].sudo().search([], order='sequence asc, id asc')
        if not setups or not base_view:
            self._remove_dynamic_view()
            self._clear_view_caches()
            return

        # مهم: اتأكد إن الفيلدات اتبنت قبل ما تعمل arch
        self._build_department_line_fields()

        arch = self._build_dynamic_arch(setups)

        inherit_view_name, _, _, key = self._get_dynamic_view_identity()
        self._remove_dynamic_view()

        self.env['ir.ui.view'].sudo().create({
            'name': inherit_view_name,
            'model': self._name,
            'inherit_id': base_view.id,
            'arch_db': arch,
            'type': 'form',
            'priority': 999999,
            'active': True,
            'key': key,
        })

        self._clear_view_caches()

    def _build_dynamic_arch(self, setups):
        root = etree.Element("data")
        xp = etree.SubElement(root, "xpath", expr="//div[@class='oe_chatter']", position="before")
        notebook = etree.SubElement(xp, "notebook")

        depts = setups.mapped('department_id')

        for dept in depts:
            page = etree.SubElement(notebook, "page", string=dept.name)

            fname = f"x_line_ids_dept_{dept.id}"
            field_lines = etree.SubElement(page, "field", name=fname)

            # منع إضافة/حذف من هنا (بس Done/Note)
            tree = etree.SubElement(field_lines, "tree", create="false", delete="false", editable="bottom")
            etree.SubElement(tree, "field", name="selected")
            etree.SubElement(tree, "field", name="name", readonly="1")
            etree.SubElement(tree, "field", name="is_locked", invisible="1", optional='hide')
            etree.SubElement(tree, "field", name="request_state", invisible="1", optional='hide')
            etree.SubElement(tree, "field", name="owner_ids", widget="many2many_tags", readonly="1")
            etree.SubElement(tree, "field", name="not_done",string='Yes' ,readonly="is_locked or request_state == 'done'")
            etree.SubElement(tree, "field", name="is_done",string='No' ,readonly="is_locked or request_state == 'done'")
            etree.SubElement(tree, "field", name="note", readonly="is_locked or request_state == 'done'")

        return etree.tostring(root, encoding="unicode")

    # -------------------------
    # Generate lines from setup items
    # -------------------------
    def _generate_lines_from_setup(self):
        for req in self:
            setups = self.env['clearance.setup'].sudo().search([], order='sequence asc, id asc')
            vals_list = []

            for setup in setups:
                # ✅ البنية الجديدة: items داخل setup
                items = setup.sorted(key=lambda x: (x.sequence, x.id))
                for item in items:
                    vals_list.append((0, 0, {
                        'setup_id': setup.id,
                        'name': item.name or '',
                        'sequence': item.sequence or 0,
                        'owner_ids': [(6, 0, setup.owner_ids.ids)],
                    }))

            if vals_list:
                req.write({'line_ids': vals_list})

    def _notify_owners(self):
        Activity = self.env["mail.activity"].sudo()
        todo_type = self.env.ref("mail.mail_activity_data_todo")

        for req in self:
            # مثال: owners جايين من line_ids -> owner_ids
            owners = req.line_ids.mapped("owner_ids")

            # لو owners عندك على setup بدل lines:
            # owners = req.line_ids.mapped("setup_id.owner_ids")

            owners = owners.filtered(lambda u: u and u.active)
            if not owners:
                continue

            # امنع تكرار نفس الشخص
            owners = owners.sorted(key=lambda u: u.id)
            owners = self.env["res.users"].browse(list(set(owners.ids)))

            # امنع تكرار Activity لو موجودة مسبقاً
            existing = Activity.search([
                ("res_model", "=", req._name),
                ("res_id", "=", req.id),
                ("activity_type_id", "=", todo_type.id),
                ("user_id", "in", owners.ids),
                ("summary", "=", "Clearance Approval"),
            ])
            already_users = set(existing.mapped("user_id").ids)

            vals_list = []
            for user in owners:
                if user.id in already_users:
                    continue
                vals_list.append({
                    "activity_type_id": todo_type.id,
                    "summary": "Clearance Approval",
                    "note": _("Please review clearance request For employee: %s") % (req.employee_id.name,),
                    "res_model_id": self.env["ir.model"]._get_id(req._name),
                    "res_id": req.id,
                    "user_id": user.id,
                    "date_deadline": fields.Date.today(),
                })

            if vals_list:
                Activity.create(vals_list)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._generate_lines_from_setup()
        records._ensure_dynamic_view()
        records._notify_owners()
        return records

    def confirmed_clearance_sheet(self):
        for record in self:
            undone_lines = record.line_ids.filtered(lambda l: not l.is_done)
            if undone_lines:
                raise ValidationError(
                    _("يوجد بعض الاقسام لم تكتمل \n : %s")
                    % ', '.join(undone_lines.mapped('name'))
                )
        self.resignation_id.is_clearance = True
        self.state = 'done'

    def action_draft(self):
        self.state = 'draft'

    def action_select_all_lines(self):
        for req in self:
            lines = req.line_ids.filtered(lambda l: not l.is_locked and l.request_state != 'done')
            lines.write({"selected": True})

    def action_unselect_all_lines(self):
        for req in self:
            req.line_ids.write({"selected": False})


    def action_mark_selected_done(self):
        for req in self:
            lines = req.line_ids.filtered(lambda l: l.selected)
            if not lines:
                raise ValidationError("اختر سطور أولاً.")

            lines.write({"is_done": True, "selected": False})
    @api.depends('line_ids.selected')
    def _compute_has_selected_lines(self):
        for req in self:
            req.has_selected_lines = any(req.line_ids.mapped('selected'))
    @api.depends('line_ids.is_done')
    def _compute_done_lines(self):
        for req in self:
            req.has_done_lines = all(req.line_ids.mapped('is_done'))