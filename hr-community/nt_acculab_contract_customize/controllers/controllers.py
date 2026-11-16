# -*- coding: utf-8 -*-
# from odoo import http


# class NtCreationProduct(http.Controller):
#     @http.route('/nt_creation_product/nt_creation_product/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/nt_creation_product/nt_creation_product/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('nt_creation_product.listing', {
#             'root': '/nt_creation_product/nt_creation_product',
#             'objects': http.request.env['nt_creation_product.nt_creation_product'].search([]),
#         })

#     @http.route('/nt_creation_product/nt_creation_product/objects/<model("nt_creation_product.nt_creation_product"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('nt_creation_product.object', {
#             'object': obj
#         })
