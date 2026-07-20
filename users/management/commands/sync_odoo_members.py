"""
Sync members from Odoo into the Django User table.

Usage:
    python manage.py sync_odoo_members                # incremental sync
    python manage.py sync_odoo_members --dry-run      # preview, no writes
    python manage.py sync_odoo_members --full         # also deactivate users
                                                        # removed from Odoo

Idempotent: safe to run every 5 minutes via cron.

How matching works:
    1. If Django user has `odoo_id` set → match by odoo_id
    2. Else if user has same `email` → match by email, then set odoo_id
    3. Else if user has same `member_code` → match by member_code
    4. Otherwise create a new user

What is NEVER overwritten by sync:
    - roles       (Django-controlled)
    - is_servant  (Django-controlled)
    - member_code (unless explicitly mapped in ODOO['fields'])
    - password    (kept as random unusable — use magic-link login instead)
    - photo, qr_code, created_by (Django-only)

Errors on a single record don't abort the whole sync — they're logged
and reported at the end.
"""
from __future__ import annotations

import secrets
from datetime import datetime

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from users.models import User
from users.odoo_client import OdooClient, OdooConfigError, get_client, parse_domain


NEVER_OVERWRITE = {
    'roles', 'is_servant', 'password', 'photo', 'qr_code',
    'created_by', 'is_superuser', 'is_staff', 'is_active',
}


class Command(BaseCommand):
    help = 'Sync members from Odoo into the Django User table.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Show what would change without writing.')
        parser.add_argument('--full', action='store_true',
                            help='Also deactivate Django users that no longer '
                                 'appear in Odoo. Default is create/update only.')
        parser.add_argument('--limit', type=int, default=None,
                            help='Fetch at most N Odoo records (for testing).')
        parser.add_argument('--quiet', action='store_true',
                            help='Only report summary, no per-record output.')

    def handle(self, *args, **opts):
        dry = opts['dry_run']
        full = opts['full']
        limit = opts['limit']
        quiet = opts['quiet']

        cfg = getattr(settings, 'ODOO', {}) or {}
        if not cfg.get('url'):
            self.stdout.write(self.style.WARNING(
                'Odoo sync disabled — ODOO_URL is not set. '
                'Add it to your .env to enable.'
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

        self.stdout.write(self.style.SUCCESS(
            f'Connected to Odoo ({client.backend_name}) at {cfg["url"]}, db={cfg["db"]}'
        ))

        # Fetch Odoo records
        model = cfg.get('model') or 'res.partner'
        domain = parse_domain(cfg.get('filter') or '[]')
        field_map = cfg.get('fields') or {}
        odoo_fields = list(field_map.keys())
        # Always fetch id + write_date for change detection
        for extra in ('id', 'write_date', 'active'):
            if extra not in odoo_fields:
                odoo_fields.append(extra)

        try:
            records = client.search_read(model, domain, odoo_fields, limit=limit)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Odoo query failed: {e}'))
            return

        self.stdout.write(f'Fetched {len(records)} record(s) from Odoo.{model}.')

        # Sync each record
        created = updated = skipped = errored = 0
        seen_odoo_ids = set()
        errors: list[tuple[int, str]] = []

        for rec in records:
            odoo_id = rec.get('id')
            if not odoo_id:
                continue
            seen_odoo_ids.add(odoo_id)

            try:
                changed, was_created = self._sync_one(
                    rec, field_map, dry=dry, quiet=quiet,
                )
                if was_created:
                    created += 1
                elif changed:
                    updated += 1
                else:
                    skipped += 1
            except Exception as e:
                errored += 1
                errors.append((odoo_id, str(e)))
                self.stderr.write(self.style.ERROR(
                    f'  ! record {odoo_id}: {e}'
                ))

        # Optionally deactivate users removed from Odoo
        deactivated = 0
        if full and not dry:
            gone = User.objects.filter(is_active=True)\
                .exclude(odoo_id__isnull=True)\
                .exclude(odoo_id__in=seen_odoo_ids)
            deactivated = gone.count()
            if deactivated:
                gone.update(is_active=False)

        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'))
        self.stdout.write(self.style.SUCCESS(
            f'  Sync summary{"  (DRY RUN)" if dry else ""}'
        ))
        self.stdout.write(self.style.SUCCESS('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'))
        self.stdout.write(f'  Created:     {created:>4}')
        self.stdout.write(f'  Updated:     {updated:>4}')
        self.stdout.write(f'  Unchanged:   {skipped:>4}')
        if full:
            self.stdout.write(f'  Deactivated: {deactivated:>4}')
        if errored:
            self.stdout.write(self.style.ERROR(f'  Errors:      {errored:>4}'))
        self.stdout.write('')

    # ── one-record sync ─────────────────────────────────────────────────
    def _sync_one(
        self,
        rec: dict,
        field_map: dict[str, str],
        *,
        dry: bool,
        quiet: bool,
    ) -> tuple[bool, bool]:
        odoo_id = rec['id']

        # Locate existing user
        user = self._find_user(rec)
        was_created = user is None

        # Build the update payload from field_map
        payload: dict = {}
        for odoo_field, django_field in field_map.items():
            if django_field in NEVER_OVERWRITE:
                continue
            value = rec.get(odoo_field)

            if django_field == 'full_name':
                # split into first/last on last space
                parts = (value or '').strip().rsplit(' ', 1)
                if len(parts) == 2:
                    payload['first_name'], payload['last_name'] = parts
                else:
                    payload['first_name'] = (value or '')[:150]
                    payload['last_name'] = ''
            elif isinstance(value, bool) and value is False and django_field in (
                'email', 'phone', 'parent_phone', 'address', 'parent_email',
            ):
                # Odoo returns False for empty string fields — normalize
                payload[django_field] = ''
            elif value is None:
                continue
            else:
                payload[django_field] = value

        payload['odoo_id'] = odoo_id
        payload['odoo_synced_at'] = timezone.now()

        # Ensure the user has a username + member_code
        if was_created:
            payload.setdefault('username', self._make_username(rec, payload))
            payload.setdefault('member_code', self._make_member_code(odoo_id))
            payload.setdefault('is_active', True)

        # Detect if anything actually changes
        if not was_created:
            unchanged = all(
                getattr(user, k) == v
                for k, v in payload.items()
                if k != 'odoo_synced_at'
            )
            if unchanged:
                return False, False

        if dry:
            action = 'create' if was_created else 'update'
            if not quiet:
                self.stdout.write(
                    f'  [dry] would {action}: {payload.get("first_name","")} '
                    f'{payload.get("last_name","")} '
                    f'(odoo_id={odoo_id})'
                )
            return True, was_created

        with transaction.atomic():
            if was_created:
                user = User(**payload)
                user.set_unusable_password()
                user.save()
            else:
                for k, v in payload.items():
                    setattr(user, k, v)
                user.save()

        if not quiet:
            action = 'created' if was_created else 'updated'
            self.stdout.write(
                f'  {action}: {user.get_full_name() or user.username} '
                f'(odoo_id={odoo_id})'
            )
        return True, was_created

    # ── helpers ─────────────────────────────────────────────────────────
    def _find_user(self, rec: dict) -> User | None:
        odoo_id = rec['id']

        # 1. odoo_id
        u = User.objects.filter(odoo_id=odoo_id).first()
        if u:
            return u

        # 2. email
        email = rec.get('email') or ''
        if isinstance(email, str) and email.strip():
            u = User.objects.filter(email__iexact=email.strip()).first()
            if u:
                return u

        return None

    def _make_username(self, rec: dict, payload: dict) -> str:
        base = (payload.get('email') or '').split('@')[0]
        if not base:
            base = (payload.get('first_name') or '').strip().lower().replace(' ', '.')
        if not base:
            base = f'odoo{rec["id"]}'
        # Guarantee uniqueness
        candidate = base
        i = 1
        while User.objects.filter(username=candidate).exists():
            i += 1
            candidate = f'{base}{i}'
        return candidate[:150]

    def _make_member_code(self, odoo_id: int) -> str:
        # Prefix so we can tell Odoo-imported members apart from manual ones
        base = f'ODO{odoo_id:06d}'
        if not User.objects.filter(member_code=base).exists():
            return base
        # Extremely unlikely collision — add random suffix
        return f'{base}{secrets.token_hex(2)}'.upper()
