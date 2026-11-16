from odoo import api, fields, models


class CancelOfferReason(models.Model):
    _name = 'cancel.offer.reason'

    name = fields.Char('Reason')


