from odoo import _, api, fields, models


class CancelJobOffer(models.Model):
    _name = 'cancel.job.offer.wiz'
    _description = 'Cancel Done Job Offer'

    # done_offer_no = fields.Many2many('hr.job.offer', string='Done Offer No.', compute='_compute_done_offer', store=True)
    cancel_reason = fields.Many2one('cancel.offer.reason', string='Cancel Reason')

    # @api.depends('done_offer_no.state')
    # def _compute_done_offer(self):
    #     print("applicant", self._context['current_id'])
    #     applicant = self._context['current_id']
    #     applicant_obj = self.env['hr.applicant'].search([('id', '=', applicant)])
    #     for offer in applicant_obj.job_offer_ids:
    #         if offer.state == 'done':
    #             # self.done_offer_no.number = offer.number
    #             print("123")
    #             print("offer no.", offer.number)
    #             self.write({
    #                 'done_offer_no': offer.number,
    #             })
    #             print("done offer", self.done_offer_no.number)

    def cancel_job_offer(self):
        model_id = self._context['current_id']
        applicant_obj = self.env['hr.applicant'].search([('id', '=', model_id)])
        job_offer_obj = self.env['hr.job.offer'].search([('id', '=', model_id)])
        if applicant_obj:
            for offer in applicant_obj.job_offer_ids:
                if offer.state == 'done':
                    offer.state = 'cancel'
                    offer.write({
                        'state': 'cancel',
                        'cancel_reason': self.cancel_reason
                    })
        elif job_offer_obj:
            for offer in job_offer_obj:
                offer.write({
                    'cancel_reason': self.cancel_reason
                })