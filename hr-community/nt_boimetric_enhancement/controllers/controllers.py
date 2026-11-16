# -*- coding: utf-8 -*-
# from odoo import http


# class AchiveTimeOf(http.Controller):
#     @http.route('/achive_time_of/achive_time_of/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/achive_time_of/achive_time_of/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('achive_time_of.listing', {
#             'root': '/achive_time_of/achive_time_of',
#             'objects': http.request.env['achive_time_of.achive_time_of'].search([]),
#         })

#     @http.route('/achive_time_of/achive_time_of/objects/<model("achive_time_of.achive_time_of"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('achive_time_of.object', {
#             'object': obj
#         })
