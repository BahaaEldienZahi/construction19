from odoo import fields, models


class RoomRoom(models.Model):
    _name = 'room.room'
    _description = 'Room'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)


class RoomBooking(models.Model):
    _name = 'room.booking'
    _description = 'Room Booking'
    _rec_name = 'name'

    name = fields.Char(string='Booking Reference')
    room_id = fields.Many2one('room.room', string='Room')
    booking_date = fields.Date(string='Booking Date')
    start_time = fields.Char(string='Start Time')
    end_time = fields.Char(string='End Time')
    start_datetime = fields.Datetime(string='Start Datetime')
    stop_datetime = fields.Datetime(string='Stop Datetime')
    organizer_id = fields.Many2one('res.users', string='Organizer')
    status = fields.Char(string='Status')
    applicant_id = fields.Many2one('hr.applicant', string='Applicant')
