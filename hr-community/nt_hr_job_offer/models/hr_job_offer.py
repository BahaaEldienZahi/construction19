from odoo import models, tools


class ResHrJobOffer(models.Model):
    _name = 'hr.job.offer'
    _inherit = ['hr.job.offer', 'nt.mail.notification.mixin']

    # def action_give_to_employee(self):
    #     super(ResHrJobOffer, self).action_give_to_employee()
    #
    #     mail_template = self.env.ref('nt_recruitment_update.email_template_offer_link')
    #     payload = {
    #         'clientCode': tools.config.get('clientcode'),
    #         'username': tools.config.get('username'),
    #         'password': tools.config.get('password'),
    #     }
    #
    #     token = self.get_access_token(payload)
    #     self.send_email(template_id=mail_template, token=token)