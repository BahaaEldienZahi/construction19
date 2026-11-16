{
    'name': "NT Mail Notification",
    'summary': "A mixin module to send email notifications using the NT API.",
    'description': """
        The NT Email Notification module provides a reusable mixin for sending email notifications.
        Features include:
        - Email validation for sender, recipients, CC, and BCC addresses.
        - Integration with NT's SendNoReplyMail API for sending emails.
        - Secure token-based authentication for API requests.
        This module is a utility for developers and can be extended or integrated into other modules.
    """,
    'author': "National Technology",
    'website': "https://nt-me.com",
    'category': 'Tools',
    'version': '0.1',
    'depends': ['base', 'mail'],
    'data': [
        # security
        'security/ir.model.access.csv',
    ],
    'demo': [],
    'installable': True,
}
