# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    project_id = fields.Many2one(
        'project.project', string='Construction Project',
        domain=[('is_construction_project', '=', True)],
        help='المشروع اللي أمر الشراء ده (خامات أو مقاول باطن) بيتكلف عليه',
    )


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    boq_line_id = fields.Many2one(
        'boq.line', string='BOQ Line',
        domain="[('project_id', '=', parent.project_id), ('is_group', '=', False)]",
        help='البند من جدول الكميات اللي البند ده من أمر الشراء بيتكلف عليه',
    )

    @api.constrains('boq_line_id', 'order_id')
    def _check_boq_line_project_match(self):
        for line in self:
            if line.boq_line_id and line.order_id.project_id and \
                    line.boq_line_id.project_id != line.order_id.project_id:
                raise ValidationError(
                    'بند الـ BOQ المختار مش تابع لنفس مشروع أمر الشراء.'
                )
