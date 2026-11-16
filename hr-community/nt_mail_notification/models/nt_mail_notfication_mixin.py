import base64
from odoo import models
import requests
import re

from odoo.exceptions import ValidationError


class NTMailNotificationMixin(models.AbstractModel):
    _name = 'nt.mail.notification.mixin'
    _description = 'Email Notification Mixin'


    def send_email(self,template_id=None,token=None,params=None):
        """
        Send email using NT SendNoReplyMail API.
        """

        if params:
            payload = self._prepare_payload_with_params(params)
        else:
            payload = self._prepare_payload(template_id)

        headers = self._prepare_headers(token)

        self._send_request(payload, headers)

    def _validate_email_addresses(self,to_emails, cc_emails=None):
        """Validate all email addresses."""
        for emails, label in [(to_emails, 'to'), (cc_emails, 'cc')]:
            if emails and not self.email_validation(emails):
                raise ValidationError(f"Invalid '{label}' email address")


    def _prepare_payload_with_params(self,params):
        """Prepare the email payload."""
        if not self.validate_payload_params(params):
            raise ValidationError("Invalid payload parameters.")

        return params

    def validate_payload_params(self, params):
        required_keys = {
            'recipients': str,
            'mailSubject': str,
            'messageContent': str,
            'isHighPriority': bool,
            'mailAttachment': list,
            'mailSignature': str
        }

        for key, expected_type in required_keys.items():
            if key not in params:
                raise ValidationError(f"Missing key '{key}' in payload parameters.")
            if not isinstance(params[key], expected_type):
                raise ValidationError(f"Key '{key}' should be of type {expected_type.__name__}.")

        for attachment in params['mailAttachment']:
            if not isinstance(attachment, dict):
                raise ValidationError("Each item in 'mailAttachment' should be a dictionary.")
            if 'fileName' not in attachment or 'base64Content' not in attachment:
                raise ValidationError("Each attachment must contain 'fileName' and 'base64Content' keys.")
            if not isinstance(attachment['fileName'], str) or not isinstance(attachment['base64Content'], str):
                raise ValidationError("'fileName' and 'base64Content' should be strings in each attachment.")

        return True


    def _prepare_payload(self,template_id=None):
        """Prepare the email payload."""

        mail_template = template_id
        if not mail_template:
            raise ValidationError("Email template not found. Please check the XML ID.")

        subject = mail_template._render_template(mail_template.subject,self._name, [self.id,])[self.id]
        email_to = mail_template._render_template(mail_template.email_to,self._name, [self.id,])[self.id]
        email_cc = mail_template._render_template(mail_template.email_cc,self._name, [self.id,])[self.id]
        body_html = mail_template._render_template(mail_template.body_html,self._name, [self.id,],engine='qweb')[self.id]
        attachment_obj = mail_template._render_template(mail_template.attachment_ids, self._name, [self.id,])[self.id]
        attachment_obj_ids = []
        for x in attachment_obj.replace('ir.attachment(', '').replace(')', '').split(','):
            if x:
                attachment_obj_ids.append(int(x))

        if not email_to:
            raise ValidationError("Email recipients not found. Please check the XML ID.")

        self._validate_email_addresses(email_to)

        payload = {
            'recipients': email_to,
            'cc': email_cc if email_cc else "",
            "mailSubject": subject if subject else "",
            "messageContent": body_html,
            "isHighPriority": False,
            "mailAttachment": [
                {
                    "fileName": file.name,
                    "base64Content": base64.b64encode(file.raw).decode('utf-8'),
                } for file in self.env['ir.attachment'].browse(attachment_obj_ids)
            ],
            "mailSignature": "NTGeneralSignature"
        }

        return payload

    def _prepare_headers(self,token=None):
        """Prepare request headers."""
        return {
            'Content-Type': 'application/json',
            'Authorization': f"Bearer {token}",
        }

    def _send_request(self, payload, headers):
        """Send the email request."""
        url = "https://sendnoreplymail.nationaltechnology.net/NT/Email/SendNoReplyMail"
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
        except requests.exceptions.RequestException as err:
            raise ValidationError(f"An error occurred while sending email: {response.text}")

    @staticmethod
    def email_validation(emails):
        """Validate email address using a regex pattern."""
        emails = emails.split(';')
        for email in emails:
            try:
                email = email.strip()
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                re.match(email_pattern, email)
            except re.error:
                raise ValidationError(f"Invalid email address: {email}")
        return True

    def get_access_token(self, payload):

        url = "https://sendnoreplymail.nationaltechnology.net/NT/Authentication/Login"

        headers = {
            'Content-Type': 'application/json'
        }

        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            response_data = response.json()
            token = response_data.get('data', {}).get('token')
            return token
        except requests.exceptions.RequestException as e:
            raise ValidationError("Failed to get token, error: {}".format(response.text))

