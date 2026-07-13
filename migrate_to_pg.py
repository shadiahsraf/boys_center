"""
Boys Center — SQLite → PostgreSQL migration helper.

Run this ONCE after you've:
  1. Installed PostgreSQL locally (or have a remote instance reachable).
  2. Created an empty database, e.g.:
        createdb boys_center
        createuser boys_user --pwprompt
        psql -c "GRANT ALL PRIVILEGES ON DATABASE boys_center TO boys_user;"
  3. Copied .env.example -> .env and filled in PG credentials.

What it does (safely):
  Step 1.  Reads the current db.sqlite3 directly (does NOT touch your .env or settings).
  Step 2.  Dumps all app data to a JSON fixture (backup_sqlite.json).
  Step 3.  Switches to your PG config (from .env), runs `migrate` to create tables.
  Step 4.  Loads the fixture into PG.
  Step 5.  Tells you to delete db.sqlite3 once you've verified everything.

If you'd rather start with a clean PG database (no migration of old data),
just skip this script and run:
    python manage.py migrate
    python seed_demo.py
"""
import os
import subprocess
import sys
from pathlib import Path

# Load .env so we know what PG config the user has set
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent
SQLITE_PATH = BASE_DIR / 'db.sqlite3'
BACKUP_PATH = BASE_DIR / 'backup_sqlite.json'


def _check_env():
    """Verify the user has PG configured before we do anything destructive."""
    has_url = bool(os.environ.get('DATABASE_URL', '').strip())
    has_vars = bool(os.environ.get('DB_NAME'))
    if not (has_url or has_vars):
        print('ERROR: No PostgreSQL config found in environment.')
        print('       Set DATABASE_URL or DB_NAME (+ DB_USER/PASSWORD/HOST/PORT) in .env first.')
        print('       See .env.example for the template.')
        sys.exit(1)


def _run(cmd, env=None, check=True):
    """Run a shell command with live output."""
    print(f'\n> {" ".join(cmd)}')
    result = subprocess.run(cmd, env={**os.environ, **(env or {})})
    if check and result.returncode != 0:
        print(f'\nCommand failed with exit code {result.returncode}')
        sys.exit(result.returncode)
    return result


def step_1_dump_sqlite():
    """Dump SQLite data to a JSON fixture (override DATABASES env to point at SQLite)."""
    if not SQLITE_PATH.exists():
        print(f'No db.sqlite3 found at {SQLITE_PATH}. Skipping dump step.')
        print('You can run `python manage.py migrate && python seed_demo.py` for a clean PG start.')
        return False

    print('\n=== STEP 1: Dump SQLite to backup_sqlite.json ===')
    # Force settings to use SQLite for this step by clearing the PG env vars.
    sqlite_env = {
        'DATABASE_URL': '',
        'DB_NAME': '',
        'DB_ENGINE': '',
    }
    cmd = [
        sys.executable, 'manage.py', 'dumpdata',
        '--natural-foreign', '--natural-primary',
        '--exclude', 'contenttypes',
        '--exclude', 'auth.permission',
        '--exclude', 'admin.logentry',
        '--exclude', 'sessions.session',
        '--indent', '2',
        '--output', str(BACKUP_PATH),
    ]
    _run(cmd, env=sqlite_env)
    size_kb = BACKUP_PATH.stat().st_size // 1024
    print(f'  -> Wrote {BACKUP_PATH.name} ({size_kb} KB)')
    return True


def step_2_migrate_pg():
    """Apply migrations to the (empty) PostgreSQL database."""
    print('\n=== STEP 2: Apply migrations to PostgreSQL ===')
    cmd = [sys.executable, 'manage.py', 'migrate']
    _run(cmd)


def step_3_load_fixture():
    """Load the SQLite backup into PG."""
    if not BACKUP_PATH.exists():
        print(f'No fixture at {BACKUP_PATH}, skipping load step.')
        return
    print('\n=== STEP 3: Load fixture into PostgreSQL ===')
    cmd = [sys.executable, 'manage.py', 'loaddata', str(BACKUP_PATH)]
    _run(cmd)


def main():
    print('Boys Center — SQLite -> PostgreSQL migration')
    print('=' * 56)

    _check_env()

    has_sqlite = step_1_dump_sqlite()
    step_2_migrate_pg()
    if has_sqlite:
        step_3_load_fixture()

    print('\n' + '=' * 56)
    print('Migration complete.')
    if has_sqlite:
        print(f'  - Backup kept at: {BACKUP_PATH}')
        print(f'  - Verify the app, then you can safely remove {SQLITE_PATH.name}')
    else:
        print('  - PG database is fresh; run `python seed_demo.py` to populate demo data.')
    print('=' * 56)


if __name__ == '__main__':
    main()
