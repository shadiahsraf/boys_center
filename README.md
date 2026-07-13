# Boys Center — Youth Club Management System

A production-grade Django web application for a multi-sport Christian youth club, with a polished public landing page, role-based authenticated dashboard, bilingual UI (English/Arabic), and dark mode.

## What's included in this build

| Area | Detail |
|------|--------|
| **Public landing page** | Visitors see a SaaS-quality marketing page at `/` with hero, sport identity cards, club stats, latest news, upcoming events, and CTA. No login required. |
| **Public news + events** | `/news/` and `/events/` pages (both list and detail) work for anonymous visitors with a clean public navbar. Logged-in users see the same content with the dashboard sidebar. |
| **Role-based dashboards** | Five distinct dashboards: Admin, Coach Manager, Coach, Parent, Youth. |
| **Token-based attendance** | Coaches generate per-session QR codes. Players scan → enter member code → check-in recorded. Duplicate prevention, expiry, late detection. |
| **Bilingual UI (EN/AR)** | Full Arabic translations with RTL support. Language toggle on every page (public navbar + topbar). |
| **Dark mode** | Polished dark theme with localStorage persistence and FOUC prevention. Toggle on every page. |
| **Parent → children linking** | Parents can be linked to youth members through the user form. |
| **Coach customization** | Coaches pick a primary sport and can be flagged as servants (خادم). |
| **Admin permissions** | Admins can add/edit/delete users, news, events. Self-deletion blocked. Last-admin protection. All deletes audited. |
| **Realistic seed data** | 200 youth, 80 parents, 11 coaches, 24 teams, 90 matches, 60 sessions, 2,115 attendance records, 346 evaluations, all generated via Faker with Coptic/Egyptian name pools. |
| **Reports** | PDF + Excel exports for attendance and evaluations. |

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env                # then edit .env with your DB creds
python manage.py migrate
python manage.py compilemessages    # builds Arabic .mo from .po
python seed_demo.py                 # lightweight demo data (or: python seed_data.py for the full set)
python manage.py runserver
```

Open http://127.0.0.1:8000 — you'll see the **public landing page** if not signed in, or your **dashboard** if you are.

## Database — PostgreSQL

The project uses **PostgreSQL** as the canonical database (SQLite is supported only as a fallback for quick offline dev when no env vars are set).

### One-time setup

1. **Install PostgreSQL** if you don't already have it.
   - **Windows / macOS**: download from <https://www.postgresql.org/download/>
   - **Linux**: `sudo apt install postgresql postgresql-contrib` (or your distro's equivalent)

2. **Create the database + user**:
   ```bash
   # As postgres superuser:
   createdb boys_center
   createuser boys_user --pwprompt          # enter a password when prompted
   psql -c "GRANT ALL PRIVILEGES ON DATABASE boys_center TO boys_user;"
   # PG 15+ also needs schema-level grants:
   psql -d boys_center -c "GRANT ALL ON SCHEMA public TO boys_user;"
   ```

3. **Configure `.env`**: copy `.env.example` to `.env` and fill in the PG credentials.
   The settings module reads either `DATABASE_URL` (single connection string) **or** the
   discrete `DB_NAME`/`DB_USER`/`DB_PASSWORD`/`DB_HOST`/`DB_PORT` variables.

4. **Apply migrations**:
   ```bash
   python manage.py migrate
   ```

5. **Seed data** (optional):
   ```bash
   python seed_demo.py
   ```

### Upgrading an existing SQLite install

If you've been running on SQLite and want to keep your data:

```bash
# After PG is set up and .env is configured:
python migrate_to_pg.py
```

The helper script:
1. Dumps your SQLite data to `backup_sqlite.json` (excluding `contenttypes`, `auth.permission`, `admin.logentry`, `sessions.session` — they get re-created).
2. Runs `migrate` against the empty PG database.
3. Loads the fixture into PG.
4. Leaves your `db.sqlite3` untouched so you can verify before deleting it.

If you'd rather start fresh on PG (no data migration), just skip the helper:
```bash
python manage.py migrate
python seed_demo.py
```

### Why PostgreSQL?

- Native `UUIDField` and `JSONField` (used for `User.id` and `User.roles`) — no JSON-as-text workarounds.
- Proper concurrency for the QR check-in flow (SQLite locks the whole file on writes).
- Production-ready migrations, full-text search, row-level locking, `CONCURRENTLY` indexes.

## Login credentials

| Role          | Username        | Password   |
|---------------|-----------------|------------|
| Admin         | `admin`         | `admin123` |
| Coach Manager | `manager`       | `pass123`  |
| Coach         | `coach_footb_0` | `pass123`  |
| Parent        | `parent_1`      | `pass123`  |
| Youth         | `youth_001`     | `pass123`  |

## Public vs. Authenticated layouts

Both layouts share the same brand and design system, but render differently based on auth state:

- **Public**: top horizontal navbar, full-width hero/marketing layout, footer at bottom.
- **Authenticated**: collapsible sidebar (left), sticky topbar (right), main content area with cards/tables.

The `news` and `events` apps render in both modes — anonymous users see them with the public navbar, while logged-in users see them inside their dashboard shell.

## Common admin tasks

### Add news
1. Sign in as admin → sidebar **News** → top-right blue **"New post"** button
2. Fill in English title + content (Arabic optional), check Published, click **Save post**

### Add an event
1. Sidebar **Events** → top-right blue **"New event"**
2. Title, type, location, start/end times, description, **Save event**

### Delete news or events
Open the article/event detail page → top-right red **"Delete"** button → confirmation page

### Add a parent and link children
1. Sidebar **Members** → **Add member**
2. Fill in account + contact info
3. Check the **Parent** role — a "Children" section appears
4. Hold Ctrl (Cmd on Mac), click multiple youth members
5. **Create member**

### Add a coach with sport + servant
1. **Members** → **Add member**
2. Check the **Coach** role — "Coach details" section appears
3. Pick a primary sport, optionally check "Is also a servant (خادم)"
4. **Create member** (role displays as e.g. "Football Coach · Servant")

### Delete a member
Members page → red trash icon on the row, OR open profile → red **"Delete"** button

## Switching language and theme

- **Language**: globe icon in topbar (or public navbar) → choose English or Arabic
- **Theme**: sun/moon icon in topbar (or public navbar). Persists in browser. Respects OS preference on first visit.

## Project structure

```
boys_center/
├── config/                   # Project settings, root URLs
├── users/                    # Custom User model (UUID, JSON roles, member code, QR)
├── attendance/               # Token-based session check-in
├── sports/                   # Teams, matches, leaderboard
├── evaluations/              # 5-star evaluations
├── events/                   # Calendar
├── news/                     # Bilingual news
├── reports/                  # PDF/Excel exports
├── locale/ar/LC_MESSAGES/    # Arabic translations (.po + compiled .mo)
├── apply_translations.py     # Translation builder helper
├── templates/
│   ├── base.html             # Renders auth or public layout based on user
│   ├── landing.html          # Public landing page
│   ├── partials/
│   │   ├── sidebar.html      # Auth sidebar
│   │   ├── public_nav.html   # Public navbar
│   │   └── public_footer.html
│   ├── dashboard/            # 5 role-specific dashboards
│   ├── attendance/           # Includes public check-in pages
│   ├── users/                # Login, list, detail, form, delete confirm, activity log
│   ├── sports/               # Teams, matches, leaderboard
│   ├── evaluations/
│   ├── news/                 # Includes _body partials for dual-layout reuse
│   ├── events/               # Same dual-layout pattern
│   └── reports/
├── static/css/app.css        # ~1,980-line design system (light + dark + public + auth)
├── seed_data.py              # Faker-based realistic seeder
└── requirements.txt
```

## Verified during this build

- `python manage.py check` → 0 issues
- 55 URLs tested across public, admin, all 5 roles → 0 failures
- Public landing renders with all sections (hero, values, news, events, CTA, footer)
- Authenticated user hitting `/en/` → redirects to `/en/dashboard/`
- News/events pages serve different layouts based on auth state
- Arabic phrases ("البويز سنتر", "آخر الأخبار", "الأحداث القادمة", etc.) render correctly on `/ar/` pages
- Dark mode toggle works on both public and authenticated pages
- Parent + child linking through form POST verified end-to-end
- Coach with `primary_sport=football` + `is_servant=True` → role display "Football Coach · Servant"
- Admin delete works for users, news, events; self-delete blocked

## Production notes

Before deploying, set the following in `.env` (or your platform's env-var system):

```bash
DJANGO_SECRET_KEY=<long random string>
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DATABASE_URL=postgres://user:pass@db-host:5432/boys_center
```

Then:
1. `pip install -r requirements.txt`
2. `python manage.py migrate`
3. `python manage.py collectstatic --noinput`
4. `python manage.py compilemessages`
5. Serve via Gunicorn + Nginx; let Nginx serve `/static/` and `/media/` directly.
