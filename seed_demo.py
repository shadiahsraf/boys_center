"""
Boys Center — LIGHTWEIGHT demo seed.
Small dataset to exercise every flow without overwhelming the UI.

Run:  python seed_demo.py
Usernames are stable so you can re-run; existing users are kept.
"""
import os
import sys
import random
import django
from datetime import datetime, timedelta, time, date

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.utils import timezone
from django.contrib.auth.hashers import make_password

from users.models import User, Role
from sports.models import (Team, Match, CoachAssignment, TrainingSchedule,
                            GoalRecord, SportType, Competition, CompetitionType)
from attendance.models import AttendanceSession, AttendanceRecord, SessionType
from evaluations.models import Evaluation
from news.models import NewsPost
from events.models import Event, EventType
from notifications.models import Notification, NotificationKind
from django.core.management import call_command

random.seed(7)
HASHED = make_password('pass123')


def upsert_user(username, first, last, roles, **extra):
    u, _ = User.objects.get_or_create(
        username=username,
        defaults={'first_name': first, 'last_name': last,
                  'email': f'{username}@boyscenter.local',
                  'roles': roles, 'password': HASHED, **extra},
    )
    # Refresh role and password every run so a re-seed isn't half-broken
    u.first_name, u.last_name, u.roles = first, last, roles
    if 'password' not in u.__dict__ or not u.password:
        u.password = HASHED
    for k, v in extra.items():
        setattr(u, k, v)
    u.save()
    return u


print("\nBoys Center -- lightweight demo seed\n")

# ── 1. STAFF ───────────────────────────────────────────────────────────────
print("[1/7] Staff accounts")
admin = upsert_user('admin', 'Father', 'Bishoy', [Role.ADMIN],
                    is_staff=True, is_superuser=True, password=HASHED)
admin.password = make_password('admin123')
admin.save(update_fields=['password'])

manager = upsert_user('manager', 'George', 'Naguib', [Role.COACH_MANAGER])
print("  [ok] admin / admin123     manager / pass123")

# ── 2. COACHES (3) ─────────────────────────────────────────────────────────
print("[2/7] Coaches")
coach_football = upsert_user('coach_football', 'Mina', 'Boutros', [Role.COACH],
                             primary_sport='football')
coach_basket = upsert_user('coach_basket', 'Mark', 'Sami', [Role.COACH],
                           primary_sport='basketball', is_servant=True)
coach_volley = upsert_user('coach_volley', 'Peter', 'Hanna', [Role.COACH],
                           primary_sport='volleyball')
all_coaches = [coach_football, coach_basket, coach_volley]
print(f"  [ok] {len(all_coaches)} coaches")

# ── 3. PARENTS (4) — last name will match their kids ───────────────────────
print("[3/7] Parents")
parent_a = upsert_user('parent_a', 'Samuel', 'Tadros', [Role.PARENT])
parent_b = upsert_user('parent_b', 'Joseph', 'Girgis', [Role.PARENT])
parent_c = upsert_user('parent_c', 'Romany', 'Khalil', [Role.PARENT])
# parent_d has BOTH parent and youth roles — to exercise multi-role gate
parent_d = upsert_user('parent_d', 'Andrew', 'Wahba', [Role.PARENT, Role.YOUTH])
parents = [parent_a, parent_b, parent_c, parent_d]
print(f"  [ok] {len(parents)} parents (one multi-role)")

# ── 4. YOUTH (8) ───────────────────────────────────────────────────────────
print("[4/7] Youth")
today = date.today()


def make_youth(username, first, last, age):
    return upsert_user(
        username, first, last, [Role.YOUTH],
        date_of_birth=today - timedelta(days=age * 365 + random.randint(0, 364)),
    )


youth_list = [
    make_youth('youth_001', 'David', 'Tadros', 14),
    make_youth('youth_002', 'Michael', 'Tadros', 12),
    make_youth('youth_003', 'Daniel', 'Girgis', 15),
    make_youth('youth_004', 'Anthony', 'Khalil', 13),
    make_youth('youth_005', 'Kirollos', 'Wahba', 16),
    make_youth('youth_006', 'Beshoy', 'Saad', 11),
    make_youth('youth_007', 'Marcus', 'Ibrahim', 14),
    make_youth('youth_008', 'Philip', 'Aziz', 17),
]
# Each youth has parent contact info on their OWN account (one account per family).
parent_specs = [
    ('Samuel Tadros',   '+201001234561', 'samuel.tadros@example.com'),
    ('Samuel Tadros',   '+201001234561', 'samuel.tadros@example.com'),  # same parent for 2 kids
    ('Joseph Girgis',   '+201001234562', 'joseph.girgis@example.com'),
    ('Romany Khalil',   '+201001234563', 'romany.khalil@example.com'),
    ('Andrew Wahba',    '+201001234564', 'andrew.wahba@example.com'),
    ('Magdy Saad',      '+201001234565', ''),
    ('Ehab Ibrahim',    '+201001234566', 'ehab.ibrahim@example.com'),
    ('Sherif Aziz',     '+201001234567', ''),
]
for y, (pname, pphone, pemail) in zip(youth_list, parent_specs):
    y.parent_name = pname
    y.parent_phone = pphone
    y.parent_email = pemail
    y.save(update_fields=['parent_name', 'parent_phone', 'parent_email'])
print(f"  [ok] {len(youth_list)} youth (with parent contact info)")

# Link parents to children
parent_a.children.set([youth_list[0], youth_list[1]])
parent_b.children.set([youth_list[2]])
parent_c.children.set([youth_list[3]])
parent_d.children.set([youth_list[4]])

# ── 5. COMPETITIONS, TEAMS + MATCHES ───────────────────────────────────────
print("[5/7] Competitions, teams, matches & training")

# Two demo competitions
league, _ = Competition.objects.get_or_create(
    name='Diocese League', sport='football',
    defaults={'competition_type': CompetitionType.LEAGUE, 'season': '2025-2026'},
)
cup, _ = Competition.objects.get_or_create(
    name='Saint Mark Cup', sport='football',
    defaults={'competition_type': CompetitionType.CUP, 'season': '2025-2026'},
)

team_football, _ = Team.objects.get_or_create(
    name='U-15 Football A', sport='football', age_group='U-15',
    defaults={'coach': coach_football},
)
team_football.coach = coach_football
team_football.members.set(youth_list[:5])
team_football.save()

team_basket, _ = Team.objects.get_or_create(
    name='U-15 Basketball A', sport='basketball', age_group='U-15',
    defaults={'coach': coach_basket},
)
team_basket.coach = coach_basket
team_basket.members.set(youth_list[3:7])
team_basket.save()

team_volley, _ = Team.objects.get_or_create(
    name='U-15 Volleyball A', sport='volleyball', age_group='U-15',
    defaults={'coach': coach_volley},
)
team_volley.coach = coach_volley
team_volley.members.set(youth_list[2:6])
team_volley.save()

# Need a second team in football for a match
team_football_b, _ = Team.objects.get_or_create(
    name='U-15 Football B', sport='football', age_group='U-15',
    defaults={'coach': coach_football},
)
team_football_b.members.set(youth_list[3:8])
team_football_b.save()

# Two completed matches, one upcoming
if Match.objects.count() < 3:
    m1 = Match.objects.create(
        sport='football', home_team=team_football, away_team=team_football_b,
        competition=league,
        scheduled_at=timezone.now() - timedelta(days=7),
        location='Main Football Field',
        home_score=3, away_score=1, is_completed=True,
    )
    # Goal records
    GoalRecord.objects.create(match=m1, player=youth_list[0], team=team_football, minute=12, points=1)
    GoalRecord.objects.create(match=m1, player=youth_list[1], team=team_football, minute=34, points=1)
    GoalRecord.objects.create(match=m1, player=youth_list[2], team=team_football, minute=78, points=1)
    GoalRecord.objects.create(match=m1, player=youth_list[5], team=team_football_b, minute=55, points=1)

    Match.objects.create(
        sport='football', home_team=team_football, away_team=team_football_b,
        competition=cup,
        scheduled_at=timezone.now() + timedelta(days=5),
        location='Main Football Field', is_completed=False,
    )

# Training schedules
TrainingSchedule.objects.get_or_create(
    sport='football', team=team_football, coach=coach_football,
    defaults={'day_of_week': 0, 'start_time': time(17, 0),
              'end_time': time(19, 0), 'location': 'Main Football Field'},
)
print("  [ok] 4 teams, matches, schedules")

# ── 6. SESSIONS + ATTENDANCE ───────────────────────────────────────────────
print("[6/7] Sessions & attendance")
sessions = []
# 1 active session today, 2 closed sessions in past week
session_specs = [
    (0, True, SessionType.TRAINING, 'football', coach_football, 'Football Training — Today'),
    (-3, False, SessionType.TRAINING, 'basketball', coach_basket, 'Basketball Practice'),
    (-7, False, SessionType.PRAYER, '', coach_football, 'Friday Prayer Meeting'),
]
for days_ago, is_open, stype, sport, coach, title in session_specs:
    sdate = today + timedelta(days=days_ago)
    s, created = AttendanceSession.objects.get_or_create(
        title=title,
        defaults={
            'session_type': stype, 'sport': sport, 'coach': coach,
            'date': sdate, 'start_time': time(17, 0), 'end_time': time(19, 0),
            'location': 'Church Hall', 'is_open': is_open,
        },
    )
    sessions.append(s)
    if created and days_ago < 0:
        # Add some attendance records for past sessions
        attending = random.sample(youth_list, k=random.randint(4, 7))
        session_dt = timezone.make_aware(datetime.combine(s.date, s.start_time))
        for p in attending:
            status = random.choices(['present', 'late'], weights=[85, 15])[0]
            AttendanceRecord.objects.create(
                session=s, user=p, status=status,
                check_in_time=session_dt + timedelta(
                    minutes=random.randint(-5, 25) if status == 'present' else random.randint(20, 40)
                ),
            )
print(f"  [ok] {len(sessions)} sessions + attendance records")

# ── 7. EVALUATIONS / NEWS / EVENTS ─────────────────────────────────────────
print("[7/7] Evaluations, news, events")
# 2-3 evals per youth
if Evaluation.objects.count() < 10:
    for y in youth_list:
        for _ in range(random.randint(1, 3)):
            Evaluation.objects.create(
                coach=random.choice(all_coaches), player=y,
                sport=random.choice(['football', 'basketball', 'volleyball']),
                performance=random.randint(3, 5),
                behavior=random.randint(3, 5),
                commitment=random.randint(3, 5),
                notes=random.choice([
                    'Great effort and team spirit this session.',
                    'Needs to focus more on positioning.',
                    'Excellent improvement in stamina!',
                    '', '',
                ]),
                created_at=timezone.now() - timedelta(days=random.randint(0, 30)),
            )

# News (3 posts)
news_specs = [
    ('Summer Camp Registration Open!', 'تسجيل مخيم الصيف مفتوح!',
     'Registration for the Boys Center summer camp is now open. Sign up by the end of the month.', True),
    ('U-15 Football wins 3-1', 'فريق تحت 15 يفوز 3-1',
     'Big congratulations to our U-15 football team for an outstanding performance last weekend.', True),
    ('New Volleyball Court Inauguration', 'افتتاح ملعب الكرة الطائرة',
     'We are excited to announce the inauguration of our new volleyball court next Sunday.', False),
]
for title, t_ar, content, is_featured in news_specs:
    NewsPost.objects.get_or_create(
        title=title,
        defaults={
            'title_ar': t_ar, 'excerpt': content[:150], 'content': content,
            'content_ar': t_ar, 'author': admin,
            'is_published': True, 'is_featured': is_featured,
        },
    )

# Events
events_specs = [
    ('Sunday Liturgy', EventType.PRAYER, 3, 8, 11),
    ('U-15 Football vs Anba Bishoy', EventType.MATCH, 6, 17, 19),
    ('Annual Sports Day', EventType.OTHER, 14, 9, 18),
    ('Parent-Coach Meeting', EventType.PARENT, 10, 19, 21),
]
for title, etype, days, sh, eh in events_specs:
    start_dt = (timezone.now() + timedelta(days=days)).replace(
        hour=sh, minute=0, second=0, microsecond=0)
    end_dt = start_dt.replace(hour=eh, minute=0)
    Event.objects.get_or_create(
        title=title,
        defaults={
            'event_type': etype, 'start_datetime': start_dt, 'end_datetime': end_dt,
            'location': 'Church Hall', 'created_by': admin,
            'description': f'{title} — join us for this scheduled event.',
        },
    )

# ── 8. PRE-MADE NOTIFICATIONS so the bell isn't empty on fresh seed ────────
# (Signals already create notifications for new records above; add a couple
# of pre-read & unread system notices for demo flavor.)
for u in [parent_a, youth_list[0]]:
    Notification.objects.get_or_create(
        recipient=u, kind=NotificationKind.SYSTEM,
        title='Welcome to Boys Center!',
        defaults={
            'message': 'Your account is ready. Explore the dashboard and check the bell for updates.',
            'is_read': False,
        },
    )

# Bible quiz questions (idempotent)
print("[bonus] Seeding Bible quiz questions")
call_command('seed_bible_questions', verbosity=0)

# ── SUMMARY ────────────────────────────────────────────────────────────────
print("\n" + "=" * 56)
print("DEMO SEED COMPLETE")
print(f"  Users:          {User.objects.count()}")
print(f"  Teams:          {Team.objects.count()}")
print(f"  Matches:        {Match.objects.count()}")
print(f"  Sessions:       {AttendanceSession.objects.count()}")
print(f"  Attendance:     {AttendanceRecord.objects.count()}")
print(f"  Evaluations:    {Evaluation.objects.count()}")
print(f"  News:           {NewsPost.objects.count()}")
print(f"  Events:         {Event.objects.count()}")
print(f"  Notifications:  {Notification.objects.count()}")
print(f"  Competitions:   {Competition.objects.count()}")
print("=" * 56)
print("\nLOGIN CREDENTIALS  (password: pass123 unless noted)")
print("  admin            / admin123     — Admin (full access)")
print("  manager          / pass123      — Coach Manager")
print("  coach_football   / pass123      — Coach")
print("  coach_basket     / pass123      — Coach (servant)")
print("  coach_volley     / pass123      — Coach")
print("  parent_a         / pass123      — Parent (2 children)")
print("  parent_b         / pass123      — Parent (1 child)")
print("  parent_c         / pass123      — Parent (1 child)")
print("  parent_d         / pass123      — Parent + Youth (multi-role)")
print("  youth_001…008    / pass123      — Youth players")
print()
