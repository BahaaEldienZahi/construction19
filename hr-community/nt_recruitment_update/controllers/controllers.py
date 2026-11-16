# -*- coding: utf-8 -*-
import uuid

from odoo import http, _
from odoo.http import request

import logging
import json
import base64

from datetime import datetime

logger = logging.getLogger(__name__)


class RecrutimentController(http.Controller):

    @http.route('/recruitment/thanks', type='http', auth="public")
    def thanks_page(self):
        return request.render("nt_recruitment_update.portal_thank_you_recruitment")

    @http.route('/recruitment/<int:rec_id>/attachment', type='http', auth="public")
    def upload_folders_form(self, rec_id):
        return request.render("nt_recruitment_update.portal_upload_files", {
            'applicant_id': rec_id
        })

    @http.route('/recruitment/<int:rec_id>/attachment/upload', methods=["POST"], auth="none", website=True)
    def upload_folders_action(self, rec_id, **post):
        application = request.env['hr.applicant'].sudo().search([('id', '=', rec_id)])
        logger.info(request.httprequest.files)
        Attachments = request.env['ir.attachment'].sudo()
        logger.info(request.httprequest.files.getlist('attachments'))
        folder_files = request.httprequest.files.getlist('attachments')
        for single_file in folder_files:
            f_name = single_file.filename.split("/")[-1]
            attachment = base64.b64encode(single_file.read()).decode()
            logger.info('attachment')
            if application:
                attachment_emp = Attachments.sudo().create({
                    'name': f_name,
                    'res_name': f_name,
                    'type': 'binary',
                    'res_model': 'hr.employee',
                    'res_id': application.emp_id.id,
                    'datas': attachment,
                })

            attachment_id = Attachments.sudo().create({
                'name': f_name,
                'res_name': f_name,
                'type': 'binary',
                'res_model': 'hr.applicant',
                'res_id': rec_id,
                'datas': attachment,
            })

        return request.redirect("/recruitment/thanks")

    @http.route('/recruitment/offer/<string:token>', type="http", auth="public", methods=['post', 'get'], website=True)
    def accept_or_reject_offer(self, token):
        offer_id = request.env['hr.job.offer'].sudo().search([('token', '=', token), ('expired', '!=', True)])
        if not offer_id:
            return request.render('website.page_404')
        api = f'/recruitment/offer/{token}/result'
        user_context = request.env['res.users'].sudo().browse(1).id
        return request.env['ir.ui.view'].sudo()._render_template(
            'nt_recruitment_update.portal_job_offer', {
                'docs': offer_id,
                'api': api
            }
        )

    @http.route(['/application/thank_page', ], auth='public', type='http', method=['GET'], website=True)
    def thank_you_page(self):
        return request.render('nt_recruitment_update.submit_thank_you_page')

    @http.route('/recruitment/offer/<string:token>/result', type='json', auth="public", methods=['post', 'get'],
                website=True)
    def job_offer_result(self, token, **post):
        decision = request.params.get('decision')
        join_date = request.params.get('availability_date')
        reject_reason = request.params.get('reject_reason')
        errors = {}
        offer_id = request.env['hr.job.offer'].sudo().search([('token', '=', token)])
        if offer_id:
            if offer_id.state == 'done':
                errors = 'Job offer already accepted before.'
            if offer_id.state == 'expired':
                errors = 'Job offer has been expired.'
            if offer_id.state in ['reject', 'cancel']:
                errors = 'Job offer already Rejected/cancelled before.'
            if not decision:
                errors = 'You should choose if the offer is accepted or rejected.'
            if decision == 'accept':
                if not join_date:
                    errors = 'The joining date is required'
            if join_date:
                join_date_formatted = datetime.strptime(join_date, "%Y-%m-%d").date()
                if join_date_formatted <= offer_id.offer_date:
                    errors = _('Please, Enter a joining date after %(date)s',
                               date=str(offer_id.offer_date))
            if errors:
                return {"success": False, "errors": errors}
            else:
                offer_id.sudo().write({
                    'state': 'done' if decision == 'accept' else 'reject',
                    'applicant_decision': 'accept' if decision == 'accept' else 'reject',
                    'availability_date': join_date if decision == 'accept' else None,
                    'reject_resason': reject_reason if decision == 'reject' else None,
                    'reject_type': 'applicant' if decision == 'reject' else None,
                })
                offer_id.applicant_id.sudo().write({'availability': join_date if decision == 'accept' else None})
                #     send attachment reminder after accept
                if decision == 'accept':
                    offer_id.applicant_id.sudo().send_attachment_reminder_manually()
                return {"success": True, "errors": False}
