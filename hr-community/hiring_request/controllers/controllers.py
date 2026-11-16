# -*- coding: utf-8 -*-
# from odoo import http


# class HiringRequest(http.Controller):
#     @http.route('/hiring_request/hiring_request', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/hiring_request/hiring_request/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('hiring_request.listing', {
#             'root': '/hiring_request/hiring_request',
#             'objects': http.request.env['hiring_request.hiring_request'].search([]),
#         })

#     @http.route('/hiring_request/hiring_request/objects/<model("hiring_request.hiring_request"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('hiring_request.object', {
#             'object': obj
#         })

