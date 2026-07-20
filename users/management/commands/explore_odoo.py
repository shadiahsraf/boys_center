"""
Explore Odoo schema + sample data — helps you discover the right filter
BEFORE running sync_odoo_members.

Usage:
    python manage.py explore_odoo                    # summary of everything
    python manage.py explore_odoo --fields           # list all fields
    python manage.py explore_odoo --tags             # list all partner categories/tags
    python manage.py explore_odoo --sample 5         # dump full data of 5 random contacts
    python manage.py explore_odoo --sample-id 1027   # dump one specific contact by ID
    python manage.py explore_odoo --distinct field   # show every distinct value of one field
    python manage.py explore_odoo --models           # list all installed Odoo models
"""
from __future__ import annotations

from collections import Counter

from django.core.management.base import BaseCommand
from django.conf import settings

from users.odoo_client import get_client, OdooConfigError


class Command(BaseCommand):
    help = 'Explore an Odoo instance to discover the right filter.'

    def add_arguments(self, parser):
        parser.add_argument('--model', default=None,
                            help='Odoo model to inspect (default: from settings)')
        parser.add_argument('--fields', action='store_true',
                            help='List every field on the model.')
        parser.add_argument('--tags', action='store_true',
                            help='List all res.partner.category (tags).')
        parser.add_argument('--models', action='store_true',
                            help='List every model installed in Odoo.')
        parser.add_argument('--sample', type=int, default=0, metavar='N',
                            help='Print full data of N random contacts.')
        parser.add_argument('--sample-id', type=int, default=None, metavar='ID',
                            help='Print full data of one specific Odoo record by ID.')
        parser.add_argument('--distinct', metavar='FIELD',
                            help='Print every distinct value of one field (with counts).')
        parser.add_argument('--limit', type=int, default=None,
                            help='Only look at first N records (for large DBs).')

    def handle(self, *args, **opts):
        cfg = getattr(settings, 'ODOO', {}) or {}
        if not cfg.get('url'):
            self.stderr.write(self.style.ERROR(
                'ODOO_URL is not set in .env. Configure it first.'
            ))
            return

        try:
            client = get_client()
        except OdooConfigError as e:
            self.stderr.write(self.style.ERROR(f'Odoo config error: {e}'))
            return
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Odoo connection failed: {e}'))
            return

        model = opts['model'] or cfg.get('model') or 'res.partner'
        self.stdout.write(self.style.SUCCESS(
            f'Connected to {cfg["url"]}  ({client.backend_name})'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'Inspecting model: {model}'
        ))
        self.stdout.write('')

        if opts['models']:
            self._list_models(client)
        elif opts['fields']:
            self._list_fields(client, model)
        elif opts['tags']:
            self._list_tags(client)
        elif opts['distinct']:
            self._distinct(client, model, opts['distinct'], opts['limit'])
        elif opts['sample']:
            self._sample(client, model, opts['sample'])
        elif opts['sample_id']:
            self._sample_one(client, model, opts['sample_id'])
        else:
            self._summary(client, model)

    # ── Summary (default) ──────────────────────────────────────────────
    def _summary(self, client, model):
        # Count total records
        try:
            all_ids = client.search_read(model, [], ['id'])
            total = len(all_ids)
        except Exception as e:
            self.stderr.write(f'Failed to count records: {e}')
            return
        self.stdout.write(f'  Total records in {model}: {total}')

        # Sample a few — get all fields on one record so user sees the shape
        sample = client.search_read(model, [], [], limit=1)
        if sample:
            all_field_names = sorted(sample[0].keys())
            self.stdout.write(f'  Fields on this model:  {len(all_field_names)}')
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('Custom fields (usually the ones you want to filter on):'))
            for f in all_field_names:
                if f.startswith('x_') or 'membership' in f.lower():
                    val = sample[0].get(f)
                    self.stdout.write(f'    {f:<40} = {val!r}')
            self.stdout.write('')
            self.stdout.write('Standard fields (first 20):')
            for f in all_field_names[:20]:
                if f.startswith('x_') or 'membership' in f.lower():
                    continue
                val = sample[0].get(f)
                self.stdout.write(f'    {f:<40} = {val!r}')

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Next steps:'))
        self.stdout.write('  • python manage.py explore_odoo --fields   → see ALL fields with types')
        self.stdout.write('  • python manage.py explore_odoo --tags     → see all tags')
        self.stdout.write('  • python manage.py explore_odoo --sample 5 → see 5 random records in full')
        self.stdout.write('  • python manage.py explore_odoo --distinct <field>')

    # ── List all fields ────────────────────────────────────────────────
    def _list_fields(self, client, model):
        sample = client.search_read(model, [], [], limit=1)
        if not sample:
            self.stdout.write('No records to inspect.')
            return
        rec = sample[0]

        # Group into custom vs standard
        custom = [f for f in rec if f.startswith('x_')]
        maybe_youth = [f for f in rec if any(
            k in f.lower() for k in
            ('member', 'youth', 'age', 'birth', 'parent', 'season', 'category',
             'type', 'kind', 'status', 'active', 'subscri', 'enroll')
        ) and not f.startswith('x_')]
        rest = [f for f in rec if f not in custom and f not in maybe_youth]

        self._print_field_group('CUSTOM FIELDS (x_...)', custom, rec)
        self._print_field_group('POTENTIALLY RELEVANT (contains member/youth/age/etc)', maybe_youth, rec)
        self._print_field_group(f'OTHER FIELDS ({len(rest)} total, first 30)', rest[:30], rec)

    def _print_field_group(self, title, names, rec):
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'━━ {title} ━━'))
        if not names:
            self.stdout.write('  (none)')
            return
        for f in sorted(names):
            val = rec.get(f)
            # Truncate long values
            display = repr(val)
            if len(display) > 60:
                display = display[:57] + '...'
            self.stdout.write(f'    {f:<40} {display}')

    # ── List categories/tags ───────────────────────────────────────────
    def _list_tags(self, client):
        try:
            tags = client.search_read('res.partner.category',
                                       [], ['id', 'name', 'parent_id'])
        except Exception as e:
            self.stderr.write(f'Failed to read tags: {e}')
            return
        self.stdout.write(self.style.SUCCESS(f'Found {len(tags)} tag(s):'))
        for t in tags:
            parent = ''
            if t.get('parent_id'):
                # parent_id is [id, 'name'] tuple
                parent = f'  (under: {t["parent_id"][1]})'
            self.stdout.write(f'  #{t["id"]:>5}  {t["name"]}{parent}')
        self.stdout.write('')
        self.stdout.write('To filter by a tag, use:')
        self.stdout.write('  ODOO_FILTER=[(\'category_id.name\', \'=\', \'your_tag_name\')]')

    # ── List installed models ──────────────────────────────────────────
    def _list_models(self, client):
        try:
            models = client.search_read('ir.model',
                                         [('transient', '=', False)],
                                         ['model', 'name'])
        except Exception as e:
            self.stderr.write(f'Failed to list models: {e}')
            return
        # Only show interesting ones (usually the club-specific + res.*)
        interesting = [m for m in models if
                       m['model'].startswith(('res.', 'membership.', 'sale.',
                                              'x_', 'summer', 'pool', 'club',
                                              'subscription'))]
        self.stdout.write(f'Found {len(models)} model(s), showing {len(interesting)} relevant:')
        for m in sorted(interesting, key=lambda x: x['model']):
            self.stdout.write(f'  {m["model"]:<40}  {m["name"]}')

    # ── Distinct values of a field ─────────────────────────────────────
    def _distinct(self, client, model, field, limit):
        try:
            records = client.search_read(model, [], [field], limit=limit)
        except Exception as e:
            self.stderr.write(f'Failed to read: {e}')
            return

        values = []
        for r in records:
            v = r.get(field)
            if isinstance(v, list) and len(v) == 2:  # many2one → [id, name]
                v = f'{v[1]} (#{v[0]})'
            elif isinstance(v, (list, tuple)):
                v = str(v)
            values.append(v)

        counter = Counter(values)
        self.stdout.write(f'Distinct values of "{field}" across {len(records)} records:')
        for value, count in counter.most_common():
            self.stdout.write(f'  {count:>6}  ×  {value!r}')

    # ── Sample N random records ────────────────────────────────────────
    def _sample(self, client, model, n):
        try:
            all_ids = client.search_read(model, [], ['id'])
        except Exception as e:
            self.stderr.write(f'Failed: {e}')
            return
        import random
        sample_ids = random.sample([r['id'] for r in all_ids], min(n, len(all_ids)))
        try:
            recs = client.search_read(model, [('id', 'in', sample_ids)], [])
        except Exception as e:
            self.stderr.write(f'Failed to read records: {e}')
            return
        for r in recs:
            self._print_record(r)

    # ── Sample one specific record by ID ───────────────────────────────
    def _sample_one(self, client, model, rec_id):
        try:
            recs = client.search_read(model, [('id', '=', rec_id)], [])
        except Exception as e:
            self.stderr.write(f'Failed to read record: {e}')
            return
        if not recs:
            self.stdout.write(f'No record with id={rec_id}')
            return
        self._print_record(recs[0])

    def _print_record(self, r):
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'━━ Record #{r.get("id")}  {r.get("name","")!r} ━━'
        ))
        for k, v in sorted(r.items()):
            if v is False or v is None or v == '':
                continue
            display = repr(v)
            if len(display) > 100:
                display = display[:97] + '...'
            self.stdout.write(f'  {k:<40} {display}')
