"""
Odoo connector — thin wrapper over XML-RPC using OdooRPC.

Reads its config from settings.ODOO (which is env-driven, so nothing
sensitive lives in the codebase). Falls back to raw XML-RPC via stdlib
if OdooRPC isn't installed, so the sync still works in constrained envs.

Usage:
    from users.odoo_client import get_client
    client = get_client()
    records = client.search_read('res.partner', [('is_member', '=', True)],
                                  ['name', 'email', 'phone'])
"""
from __future__ import annotations

import ast
from typing import Any, Iterable
from urllib.parse import urlparse

from django.conf import settings


class OdooConfigError(RuntimeError):
    """Raised when required Odoo settings are missing."""


class OdooClient:
    """Uniform interface over odoorpc or xmlrpc.client — whichever is available."""

    def __init__(self, url: str, db: str, username: str, password: str):
        self.url = url.rstrip('/')
        self.db = db
        self.username = username
        self.password = password
        self._backend = None
        self._impl = None  # 'odoorpc' or 'xmlrpc'
        self._uid = None

    # ── Connect ───────────────────────────────────────────────────────────
    def connect(self):
        try:
            import odoorpc
            u = urlparse(self.url)
            host = u.hostname
            if not host:
                raise OdooConfigError(f'Bad Odoo URL: {self.url!r}')
            port = u.port or (443 if u.scheme == 'https' else 8069)
            protocol = 'jsonrpc+ssl' if u.scheme == 'https' else 'jsonrpc'
            self._backend = odoorpc.ODOO(host, protocol=protocol, port=port, timeout=60)
            self._backend.login(self.db, self.username, self.password)
            self._impl = 'odoorpc'
            self._uid = self._backend.env.uid
        except ImportError:
            # Fallback: stdlib XML-RPC
            import xmlrpc.client as xmlrpc
            common = xmlrpc.ServerProxy(f'{self.url}/xmlrpc/2/common', allow_none=True)
            self._uid = common.authenticate(self.db, self.username, self.password, {})
            if not self._uid:
                raise OdooConfigError('Odoo authentication failed (XML-RPC).')
            self._backend = xmlrpc.ServerProxy(f'{self.url}/xmlrpc/2/object', allow_none=True)
            self._impl = 'xmlrpc'
        return self

    @property
    def backend_name(self) -> str:
        return self._impl or 'not-connected'

    # ── Read ──────────────────────────────────────────────────────────────
    def search_read(
        self,
        model: str,
        domain: list,
        fields: Iterable[str],
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch records matching a domain. Same signature for both backends."""
        fields = list(fields)
        if self._impl == 'odoorpc':
            Model = self._backend.env[model]
            ids = Model.search(domain, limit=limit) if limit else Model.search(domain)
            return Model.read(ids, fields) if ids else []
        # xmlrpc path
        kwargs = {'fields': fields}
        if limit:
            kwargs['limit'] = limit
        return self._backend.execute_kw(
            self.db, self._uid, self.password,
            model, 'search_read', [domain], kwargs,
        )


def parse_domain(raw: str) -> list:
    """Turn a `.env` string like `[('is_member','=',True)]` into a real list.
    Uses ast.literal_eval for safety (no exec/eval)."""
    if not raw or not raw.strip():
        return []
    try:
        parsed = ast.literal_eval(raw)
    except (SyntaxError, ValueError) as e:
        raise OdooConfigError(f'ODOO_FILTER is not valid Python literal: {e}')
    if not isinstance(parsed, list):
        raise OdooConfigError('ODOO_FILTER must be a list of tuples.')
    return parsed


def get_client() -> OdooClient:
    """Build + connect an Odoo client from Django settings."""
    cfg = getattr(settings, 'ODOO', None) or {}
    missing = [k for k in ('url', 'db', 'username', 'password') if not cfg.get(k)]
    if missing:
        raise OdooConfigError(
            f'Missing Odoo settings: {", ".join(missing)}. '
            'Set ODOO_URL / ODOO_DB / ODOO_USERNAME / ODOO_PASSWORD in your .env.'
        )
    return OdooClient(
        url=cfg['url'], db=cfg['db'],
        username=cfg['username'], password=cfg['password'],
    ).connect()
