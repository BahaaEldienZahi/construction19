# -*- coding: utf-8 -*-
# from odoo import http


# class NtResignation(http.Controller):
#     @http.route('/nt_resignation/nt_resignation', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/nt_resignation/nt_resignation/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('nt_resignation.listing', {
#             'root': '/nt_resignation/nt_resignation',
#             'objects': http.request.env['nt_resignation.nt_resignation'].search([]),
#         })

#     @http.route('/nt_resignation/nt_resignation/objects/<model("nt_resignation.nt_resignation"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('nt_resignation.object', {
#             'object': obj
#         })

