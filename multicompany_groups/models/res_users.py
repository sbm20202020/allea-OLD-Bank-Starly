# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from collections import defaultdict
from odoo import fields, models, api, SUPERUSER_ID, tools , _
from odoo.exceptions import AccessError
from odoo.tools.safe_eval import safe_eval
from odoo.osv import expression
from odoo.tools import pycompat, sql

_logger = logging.getLogger(__name__)
_schema = logging.getLogger(__name__[:-7] + '.schema')

# class Many2manyMultiCompany(fields.Many2many):
#
#     def update_db(self, model, columns):
#         cr = model._cr
#         # Do not reflect relations for custom fields, as they do not belong to a
#         # module. They are automatically removed when dropping the corresponding
#         # 'ir.model.field'.
#         if not self.manual:
#             model.pool.post_init(
#                 model.env['ir.model.relation']._reflect_relation,
#                 model, self.relation, self._module)
#         if not sql.table_exists(cr, self.relation):
#             comodel = model.env[self.comodel_name]
#             query = """
#                 CREATE TABLE "{rel}" ("{id1}" INTEGER NOT NULL,
#                                       "{id2}" INTEGER NOT NULL,
#                                       "company_id" INTEGER NOT NULL,
#                                       UNIQUE("{id1}","{id2}","company_id"));
#                 COMMENT ON TABLE "{rel}" IS %s;
#                 CREATE INDEX ON "{rel}" ("{id1}");
#                 CREATE INDEX ON "{rel}" ("{id2}")
#                 CREATE INDEX ON "{rel}" ("company_id")
#             """.format(rel=self.relation, id1=self.column1, id2=self.column2)
#             cr.execute(
#                 query, ['RELATION BETWEEN %s AND %s' %
#                         (model._table, comodel._table)])
#             _schema.debug("Create table %r: m2m relation between %r and %r",
#                           self.relation, model._table, comodel._table)
#             model.pool.post_init(self.update_db_foreign_keys, model)
#             return True
#
#     def update_db_foreign_keys(self, model):
#         """ Add the foreign keys corresponding to the field's relation table. """
#         cr = model._cr
#         reflect = model.env['ir.model.constraint']._reflect_constraint
#         res = super(Many2manyMultiCompany, self).update_db_foreign_keys(model)
#         # create foreign key references with ondelete=cascade, unless the targets are SQL views
#         sql.add_foreign_key(cr, self.relation, 'company_id', 'res_company', 'id', 'cascade')
#         reflect(model, '%s_%s_fkey' % (self.relation, 'companu_id'), 'f', None, self._module)
#         return res
#
#     def read(self, records):
#
#         comodel = records.env[self.comodel_name]
#
#         # String domains are supposed to be dynamic and evaluated on client-side
#         # only (thus ignored here).
#         domain = self.domain if isinstance(self.domain, list) else []
#         wquery = comodel._where_calc(domain)
#         comodel._apply_ir_rules(wquery, 'read')
#         order_by = comodel._generate_order_by(None, wquery)
#         from_c, where_c, where_params = wquery.get_sql()
#         company_id = records.env.cr.execute(
#             '''
#             SELECT
#                 company_id
#             FROM
#                 res_users
#             WHERE
#                 id = %s
#             ''', (records.env.context.get('uid', 0), ))
#         company_id = records.env.cr.fetchall()
#         company_id = company_id and company_id[0][0]
#         company_id = company_id or records.env.user.company_id.id
#         query = """ SELECT {rel}.{id1}, {rel}.{id2} FROM {rel}, {from_c}
#                     WHERE {where_c} AND
#                           {rel}.{id1} IN %s AND
#                           {rel}.{id2} = {tbl}.id AND
#                           {rel}.company_id={company}
#                     {order_by} {limit} OFFSET {offset}
#                 """.format(rel=self.relation, id1=self.column1, id2=self.column2,
#                            tbl=comodel._table, from_c=from_c, where_c=where_c or '1=1',
#                            company=company_id,
#                            limit=(' LIMIT %d' % self.limit) if self.limit else '',
#                            offset=0, order_by=order_by)
#         where_params.append(tuple(records.ids))
#
#         # retrieve lines and group them by record
#         group = defaultdict(list)
#         records._cr.execute(query, where_params)
#         for row in records._cr.fetchall():
#             group[row[0]].append(row[1])
#
#         # store result in cache
#         cache = records.env.cache
#         for record in records:
#             cache.set(record, self, tuple(group[record.id]))
#
#     def write(self, records, value, create=False):
#         cr = records._cr
#         comodel = records.env[self.comodel_name]
#         company_id = records.env.cr.execute(
#             '''
#             SELECT
#                 company_id
#             FROM
#                 res_users
#             WHERE
#                 id = %s
#             ''', (records.env.user.id if records.env.user else 1, ))
#         company_id = records.env.cr.fetchall()
#         company_id = company_id and company_id[0][0]
#         parts = dict(rel=self.relation,
#                      id1=self.column1,
#                      id2=self.column2,
#                      company=company_id)
#
#         clear = False           # whether the relation should be cleared
#         links = {}              # {id: True (link it) or False (unlink it)}
#
#         for act in (value or []):
#             if not isinstance(act, (list, tuple)) or not act:
#                 continue
#             if act[0] == 0:
#                 for record in records:
#                     links[comodel.create(act[2]).id] = True
#             elif act[0] == 1:
#                 comodel.browse(act[1]).write(act[2])
#             elif act[0] == 2:
#                 comodel.browse(act[1]).unlink()
#             elif act[0] == 3:
#                 links[act[1]] = False
#             elif act[0] == 4:
#                 links[act[1]] = True
#             elif act[0] == 5:
#                 clear = True
#                 links.clear()
#             elif act[0] == 6:
#                 clear = True
#                 links = dict.fromkeys(act[2], True)
#
#         if clear and not create:
#             # remove all records for which user has access rights
#             clauses, params, tables = comodel.env['ir.rule'].domain_get(comodel._name)
#             cond = " AND ".join(clauses) if clauses else "1=1"
#             query = """ DELETE FROM {rel} USING {tables}
#                         WHERE {rel}.{id1} IN %s AND
#                               {rel}.{id2}={table}.id AND
#                               {rel}.company_id={company} AND {cond}
#                     """.format(table=comodel._table,
#                                tables=','.join(tables),
#                                cond=cond,
#                                **parts)
#             cr.execute(query, [tuple(records.ids)] + params)
#
#         # link records to the ids such that links[id] = True
#         if any(links.values()):
#             # beware of duplicates when inserting
#             query = """ INSERT INTO {rel} ({id1}, {id2}, company_id)
#                         (SELECT a, b, {company} FROM unnest(%s) AS a, unnest(%s) AS b)
#                         EXCEPT (SELECT {id1}, {id2}, company_id FROM {rel}
#                                 WHERE {id1} IN %s AND company_id={company})
#                     """.format(**parts)
#             ids = [id for id, flag in links.items() if flag]
#             for sub_ids in cr.split_for_in_conditions(ids):
#                 cr.execute(query, (records.ids, list(sub_ids), tuple(records.ids)))
#
#         # unlink records from the ids such that links[id] = False
#         if not all(links.values()):
#             query = """ DELETE FROM {rel}
#                         WHERE {id1} IN %s AND {id2} IN %s AND company_id={company}
#                     """.format(**parts)
#             ids = [id for id, flag in links.items() if not flag]
#             for sub_ids in cr.split_for_in_conditions(ids):
#                 cr.execute(query, (tuple(records.ids), sub_ids))
#
#
# class Users(models.Model):
#
#     _inherit = 'res.users'
#
#     def _default_groups(self):
#         return super(Users, self)._default_groups()
#
#     groups_id = Many2manyMultiCompany( 'res.groups', 'res_groups_users_rel', 'uid', 'gid', string='Groups', default=_default_groups)
#
#     def write(self, values):
#         group_multi_company = self.env.ref('base.group_multi_company', False)
#         if values.get('company_ids'):
#             for user in self:
#                 removed = list(set(user.company_ids.ids) -
#                                set(values['company_ids'][0][2]))
#                 if removed:
#                     self._cr.execute(
#                         '''
#                         DELETE FROM
#                             res_groups_users_rel
#                         WHERE
#                             uid = %s AND company_id IN %s''',
#                         (user.id, tuple(removed)))
#                 else:
#                     added = list(set(values['company_ids'][0][2]) -
#                                  set(user.company_ids.ids))
#                     for company in added:
#                         self.env.cr.execute(
#                             '''
#                             INSERT INTO
#                                 res_groups_users_rel
#                             (uid, gid, company_id)
#                             (SELECT
#                                 uid,
#                                 gid,
#                                 %s
#                             FROM
#                                 res_groups_users_rel
#                             WHERE
#                                 uid=%s AND company_id=%s)
#                             ON CONFLICT DO NOTHING
#                             ''',
#                             (company, user.id,
#                              self.env.user.company_id.id))
#                         if group_multi_company:
#                             self.env.cr.execute(
#                                 '''
#                                 INSERT INTO
#                                    res_groups_users_rel (uid, gid, company_id)
#                                 VALUES
#                                    (%s, %s, %s)
#                                 ON CONFLICT DO NOTHING
#                             ''', (user.id, group_multi_company.id, company))
#
#         res = super(Users, self).write(values)
#         return res
#
#     # @api.model
#     # def has_group(self, group_ext_id):
#     #     # use singleton's id if called on a non-empty recordset, otherwise
#     #     # context uid
#     #     uid = self.id or self._uid
#     #     return self.sudo(user=uid)._has_group(group_ext_id)
#
#     # @api.model
#     # @tools.ormcache('self._uid', 'group_ext_id')
#     # def _has_group(self, group_ext_id):
#     #     """Checks whether user belongs to given group.
#     #
#     #     :param str group_ext_id: external ID (XML ID) of the group.
#     #        Must be provided in fully-qualified form (``module.ext_id``), as there
#     #        is no implicit module to use..
#     #     :return: True if the current user is a member of the group with the
#     #        given external ID (XML ID), else False.
#     #     """
#     #     assert group_ext_id and '.' in group_ext_id, \
#     #         "External ID must be fully qualified"
#     #     module, ext_id = group_ext_id.split('.')
#     #     self._cr.execute(
#     #         """
#     #         SELECT
#     #             1
#     #         FROM
#     #             res_groups_users_rel
#     #         WHERE
#     #             company_id=%s AND uid=%s AND gid IN
#     #             (SELECT
#     #                res_id
#     #              FROM
#     #                ir_model_data
#     #              WHERE
#     #                module=%s AND name=%s)""",
#     #         (self.env.user.company_id.id, self._uid, module, ext_id))
#     #     return bool(self._cr.fetchone())
#     # # for a few places explicitly clearing the has_group cache
#     # has_group.clear_cache = _has_group.clear_cache
#
# class Groups(models.Model):
#
#     _inherit = 'res.groups'
#
#     users = Many2manyMultiCompany('res.users', 'res_groups_users_rel', 'gid', 'uid')
#
#     def write(self, values):
#         res = super(Groups, self).write(values)
#         if values.get('users') or values.get('implied_ids'):
#             # add all implied groups (to all users of each group)
#             self._cr.execute(
#                 """DELETE FROM
#                       res_groups_users_rel
#                    WHERE
#                       company_id IS NULL""",
#                 (tuple(self.ids), ))
#             for group in self:
#                 self._cr.execute("""
#                     WITH RECURSIVE group_imply(gid, hid) AS (
#                         SELECT gid, hid
#                           FROM res_groups_implied_rel
#                          UNION
#                         SELECT i.gid, r.hid
#                           FROM res_groups_implied_rel r
#                           JOIN group_imply i ON (i.hid = r.gid)
#                     )
#                     INSERT INTO res_groups_users_rel (gid, uid, company_id)
#                          SELECT i.hid, r.uid, r.company_id
#                            FROM group_imply i, res_groups_users_rel r
#                           WHERE r.gid = i.gid
#                             AND i.gid = %(gid)s
#                          EXCEPT
#                          SELECT r.gid, r.uid, r.company_id
#                            FROM res_groups_users_rel r
#                            JOIN group_imply i ON (r.gid = i.hid)
#                           WHERE i.gid = %(gid)s
#                 """, dict(gid=group.id))
#         return res
#
#
# class Company(models.Model):
#
#     _inherit = 'res.company'
#
#     @api.model
#     def create(self, vals):
#         """When a new company is created the admin user and the user who is
#         creating the company will have the same groups that they have in the
#         current company at the moment they are creating the new company."""
#         res = super(Company, self).create(vals)
#         admin = self.env['res.users'].browse(SUPERUSER_ID)
#         admin += self.env.user
#         users = admin.exists()
#         for user in users:
#             self.env.cr.execute(
#                 '''
#                 INSERT INTO
#                     res_groups_users_rel
#                 (uid, gid, company_id)
#                 (SELECT
#                     uid,
#                     gid,
#                     %s
#                  FROM
#                     res_groups_users_rel
#                  WHERE
#                     uid=%s AND company_id=%s)''',
#                 (res.id, user.id, user.company_id.id))
#             return res
#
#
# class IrRule(models.Model):
#     _inherit = 'ir.rule'
#
#     @api.model
#     @tools.ormcache('self._uid', 'model_name', 'mode')
#     def _compute_domain(self, model_name, mode="read"):
#         if mode not in self._MODES:
#             raise ValueError('Invalid mode: %r' % (mode,))
#
#         if self._uid == SUPERUSER_ID:
#             return None
#
#         query = """
#         SELECT
#             r.id
#         FROM
#             ir_rule r
#         JOIN
#             ir_model m ON (r.model_id=m.id)
#         WHERE
#             m.model=%s AND r.active AND r.perm_{mode} AND
#             (r.id IN (SELECT
#                         rule_group_id
#                       FROM
#                         rule_group_rel rg
#                       JOIN
#                         res_groups_users_rel gu ON (rg.group_id=gu.gid)
#                       WHERE
#                         gu.uid=%s AND gu.company_id=%s) OR r.global)
#                 """.format(mode=mode)
#         self._cr.execute(
#             query, (model_name, self._uid, self.env.user.company_id.id))
#         rule_ids = [row[0] for row in self._cr.fetchall()]
#         if not rule_ids:
#             return []
#
#         # browse user and rules as SUPERUSER_ID to avoid access errors!
#         eval_context = self._eval_context()
#         user_groups = self.env.user.groups_id
#         global_domains = []                     # list of domains
#         group_domains = []                      # list of domains
#         for rule in self.browse(rule_ids).sudo():
#             # evaluate the domain for the current user
#             dom = safe_eval(rule.domain_force,
#                             eval_context) if rule.domain_force else []
#             dom = expression.normalize_domain(dom)
#             if not rule.groups:
#                 global_domains.append(dom)
#             elif rule.groups & user_groups:
#                 group_domains.append(dom)
#
#         # combine global domains and group domains
#         if not group_domains:
#             return expression.AND(global_domains)
#         return expression.AND(global_domains + [expression.OR(group_domains)])
#
#
# class IrModelAccess(models.Model):
#     _inherit = 'ir.model.access'
#     _description = 'Model Access'
#
#     @api.model
#     def check_groups(self, group):
#         """ Check whether the current user has the given group. """
#         grouparr = group.split('.')
#         if not grouparr:
#             return False
#         self._cr.execute(
#             """
#             SELECT
#                 1
#             FROM
#                 res_groups_users_rel
#             WHERE
#                 uid=%s AND company_id=%s AND gid IN (SELECT
#                                       res_id
#                                    FROM
#                                       ir_model_data
#                                    WHERE
#                                       module=%s AND name=%s)""",
#             (self._uid, self.env.user.company_id.id,
#              grouparr[0], grouparr[1],))
#         return bool(self._cr.fetchone())
#
#     # The context parameter is useful when the method translates error messages.
#     # But as the method raises an exception in that case,  the key 'lang' might
#     # not be really necessary as a cache key, unless the `ormcache_context`
#     # decorator catches the exception (it does not at the moment.)
#     # @api.model
#     # @tools.ormcache_context('self._uid', 'model', 'mode',
#     #                         'raise_exception', keys=('lang',))
#     # def check(self, model, mode='read', raise_exception=True):
#     #     if self._uid == 1:
#     #         # User root have all accesses
#     #         return True
#     #
#     #     assert isinstance(model, pycompat.string_types), \
#     #         'Not a model name: %s' % (model,)
#     #     assert mode in ('read', 'write', 'create', 'unlink'), \
#     #         'Invalid access mode'
#     #
#     #     # TransientModel records have no access rights, only an implicit access
#     #     # rule
#     #     if model not in self.env:
#     #         _logger.error('Missing model %s', model)
#     #     elif self.env[model].is_transient():
#     #         return True
#     #
#     #     # We check if a specific rule exists
#     #     self._cr.execute(
#     #         """
#     #         SELECT
#     #             MAX(CASE WHEN perm_{mode} THEN 1 ELSE 0 END)
#     #         FROM
#     #             ir_model_access a
#     #         JOIN
#     #             ir_model m ON (m.id = a.model_id)
#     #         JOIN
#     #             res_groups_users_rel gu ON (gu.gid = a.group_id)
#     #         WHERE
#     #             m.model = %s AND gu.uid = %s AND gu.company_id=%s AND
#     #         a.active IS TRUE""".format(mode=mode),
#     #         (model, self._uid, self.env.user.company_id.id))
#     #     r = self._cr.fetchone()[0]
#     #
#     #     if not r:
#     #         # there is no specific rule. We check the generic rule
#     #         self._cr.execute(
#     #             """
#     #             SELECT
#     #                 MAX(CASE WHEN perm_{mode} THEN 1 ELSE 0 END)
#     #             FROM
#     #                 ir_model_access a
#     #             JOIN
#     #                 ir_model m ON (m.id = a.model_id)
#     #             WHERE
#     #                 a.group_id IS NULL AND m.model = %s AND
#     #                 a.active IS TRUE""".format(mode=mode),
#     #             (model,))
#     #         r = self._cr.fetchone()[0]
#     #
#     #     if not r and raise_exception:
#     #         groups = '\n\t'.join(
#     #             '- %s' % g for g in self.group_names_with_access(model, mode))
#     #         msg_heads = {
#     #             # Messages are declared in extenso so they are properly
#     #             # exported in translation terms
#     #             'read':
#     #             _("Sorry, you are not allowed to access this document."),
#     #             'write':
#     #             _("Sorry, you are not allowed to modify this document."),
#     #             'create':
#     #             _("Sorry, you are not allowed to create this kind of "
#     #               "document."),
#     #             'unlink':
#     #             _("Sorry, you are not allowed to delete this document."),
#     #         }
#     #         if groups:
#     #             msg_tail = _(
#     #                 "Only users with the following access level are "
#     #                 "currently allowed to do that"
#     #             ) + ":\n%s\n\n(" + _("Document model") + ": %s)"
#     #             msg_params = (groups, model)
#     #         else:
#     #             msg_tail = _(
#     #                 "Please contact your system administrator if you "
#     #                 "think this is an error."
#     #             ) + "\n\n(" + _("Document model") + ": %s)"
#     #             msg_params = (model,)
#     #         _logger.info(
#     #             'Access Denied by ACLs for operation: %s, uid: %s, model: %s',
#     #             mode, self._uid, model)
#     #         msg = '%s %s' % (msg_heads[mode], msg_tail)
#     #         raise AccessError(msg % msg_params)
#     #
#     #     return bool(r)
