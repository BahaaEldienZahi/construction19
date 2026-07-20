# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class SiteProgressPhoto(models.Model):
    """صور تقدم الأعمال — Site Progress Photo Documentation"""
    _name = 'site.progress.photo'
    _description = 'Site Progress Photo'
    _inherit = ['mail.thread']
    _order = 'date desc, id desc'

    name = fields.Char(string='Photo Title', required=True)
    project_id = fields.Many2one(
        'project.project', string='Project', required=True,
        domain=[('is_construction_project', '=', True)], tracking=True,
    )
    company_id = fields.Many2one(related='project_id.company_id', store=True, readonly=True)
    date = fields.Date(default=fields.Date.context_today, required=True, tracking=True)
    taken_by = fields.Many2one('res.users', string='Taken By', default=lambda self: self.env.user)

    image = fields.Image(string='Photo', required=True, max_width=4096, max_height=4096)
    location = fields.Char(string='Location / Area')
    boq_line_ids = fields.Many2many(
        'boq.line', 'site_progress_photo_boq_line_rel',
        'photo_id', 'boq_line_id', string='Related BOQ Lines',
        domain="[('project_id', '=', project_id), ('is_group', '=', False)]",
    )
    daily_report_id = fields.Many2one(
        'site.daily.report', string='Daily Report',
        domain="[('project_id', '=', project_id)]",
    )
    tag_ids = fields.Many2many(
        'site.progress.photo.tag', string='Tags',
    )
    description = fields.Text(string='Description')


class SiteProgressPhotoTag(models.Model):
    _name = 'site.progress.photo.tag'
    _description = 'Progress Photo Tag'
    _order = 'name'

    name = fields.Char(string='Tag', required=True)
    color = fields.Integer(string='Color Index', default=0)
