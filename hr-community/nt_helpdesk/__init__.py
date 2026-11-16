# -*- coding: utf-8 -*-

from . import models
from . import wizard


def pre_init_hook(env):
    cr = env.cr
    # When nt_helpdesk installs, category_id on helpdesk_ticket changes comodel
    # from helpdesk.ticket.category (table: helpdesk_ticket_category) to
    # helpdesk.category (table: helpdesk_category).  Odoo drops the old FK and
    # adds a new one; that ADD fails if any category_id values don't exist in
    # helpdesk_category.  Null them out only when the old FK is still in place.
    cr.execute("""
        SELECT 1
        FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        JOIN pg_class r ON r.oid = c.confrelid
        WHERE c.contype = 'f'
          AND t.relname = 'helpdesk_ticket'
          AND c.conname = 'helpdesk_ticket_category_id_fkey'
          AND r.relname = 'helpdesk_ticket_category'
    """)
    if cr.fetchone():
        cr.execute("UPDATE helpdesk_ticket SET category_id = NULL WHERE category_id IS NOT NULL")