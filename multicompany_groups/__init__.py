# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from odoo import SUPERUSER_ID, api
from . import models


# _logger = logging.getLogger(__name__)
#
# def generate_multicompany_groups(cr):
#     with api.Environment.manage():
#         env = api.Environment(cr, SUPERUSER_ID, {})
#         users = env['res.users'].search(
#             ['|', ('active', '=', False), ('active', '=', True)])
#         env.cr.execute(
#             '''
#     ALTER TABLE
#         res_groups_users_rel
#     ADD
#         COLUMN company_id integer,
#     ADD
#         FOREIGN KEY(company_id) REFERENCES res_company(id) ON DELETE CASCADE,
#     DROP CONSTRAINT
#         res_groups_users_rel_gid_uid_key,
#     ADD  CONSTRAINT
#         res_groups_users_rel_gid_uid_key UNIQUE (gid, uid, company_id);
#     CREATE INDEX ON res_groups_users_rel(company_id);
#             ''')
#         companies = env['res.company'].search([])
#         for user in users:
#             current_company = user.company_id
#             env.cr.execute(
#                 '''
#                 UPDATE
#                     res_groups_users_rel
#                 SET
#                     company_id=%s
#                 WHERE
#                     uid=%s AND
#                     company_id IS NULL
#                 ''', (current_company.id, user.id)
#             )
#             for company in (user.company_ids - current_company):
#                 env.cr.execute(
#                     '''
#                     INSERT INTO res_groups_users_rel (uid, gid, company_id)
#                     (SELECT
#                         uid,
#                         gid,
#                         %s
#                      FROM
#                         res_groups_users_rel
#                      WHERE
#                         uid=%s AND
#                         company_id=%s)
#                        ''', (company.id, user.id, current_company.id))
#
#         for company in (companies - env.user.company_ids):
#             env.cr.execute(
#                 '''
#                 INSERT INTO res_groups_users_rel (uid, gid, company_id)
#                 (SELECT
#                     uid,
#                     gid,
#                     %s
#                     FROM
#                     res_groups_users_rel
#                     WHERE
#                     uid=%s AND
#                     company_id=%s)
#                     ''', (company.id, env.user.id, env.user.company_id.id))
#
#
# def pre_init_hook(cr):
#     generate_multicompany_groups(cr)
