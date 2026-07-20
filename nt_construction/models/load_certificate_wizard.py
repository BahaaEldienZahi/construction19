# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class LoadCertificateFromWMWizard(models.TransientModel):
    """Wizard to load BOQ Payment Certificate lines from a confirmed Work Measurement."""
    _name = 'load.certificate.from.wm.wizard'
    _description = 'Load Certificate from Work Measurement Wizard'

    certificate_id = fields.Many2one('boq.payment.certificate', required=True, readonly=True)
    work_measurement_id = fields.Many2one(
        'work.measurement', string='Work Measurement', required=True,
        domain="[('project_id', '=', certificate_project_id), ('state', '=', 'confirmed')]",
    )
    certificate_project_id = fields.Many2one(related='certificate_id.project_id', readonly=True)
    measurement_total = fields.Monetary(
        related='work_measurement_id.total_executed_value', string='Total Executed',
        currency_field='certificate_currency_id',
    )
    certificate_currency_id = fields.Many2one(related='certificate_id.currency_id', readonly=True)

    def action_load(self):
        self.ensure_one()
        cert = self.certificate_id
        wm = self.work_measurement_id

        if not wm.summary_line_ids:
            wm.action_generate_summary()

        # Remove existing draft lines
        cert.line_ids.unlink()

        # Create new lines from WM summary
        for summary in wm.summary_line_ids:
            self.env['boq.payment.certificate.line'].create({
                'certificate_id': cert.id,
                'boq_line_id': summary.boq_line_id.id,
                'quantity_this_period': summary.quantity_executed,
            })

        # Link the WM to the certificate
        wm.payment_certificate_id = cert.id
        wm.state = 'linked'

        # Set period from/to from daily report dates
        if wm.daily_report_ids:
            dates = wm.daily_report_ids.mapped('date')
            cert.write({
                'period_from': min(dates),
                'period_to': max(dates),
            })

        return {'type': 'ir.actions.act_window_close'}
