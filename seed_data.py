"""
Boys Center — Realistic seed data generator.
Run: python seed_data.py
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
from faker import Faker

from users.models import User, Role, ActivityLog
from sports.models import (Team, Match, CoachAssignment,
                            TrainingSchedule, GoalRecord, SportType)
from attendance.models import AttendanceSession, AttendanceRecord, SessionType
from evaluations.models import Evaluation
from news.models import NewsPost
from events.models import Event, EventType

random.seed(42)
fake = Faker()
Faker.seed(42)

# ─── EGYPTIAN/COPTIC NAMES (mix of common Christian Egyptian first/last names) ──
COPTIC_FIRST_NAMES = [
    'Mina', 'Mark', 'Peter', 'John', 'Michael', 'Andrew', 'Mario', 'Beshoy', 'Bishoy',
    'Samuel', 'Karim', 'David', 'George', 'Kirollos', 'Anthony', 'Joseph', 'Matthew',
    'Philip', 'Thomas', 'Reuben', 'Marcus', 'Daniel', 'Steven', 'Anthonious', 'Arsanius',
    'Pavly', 'Pavlos', 'Pakhom', 'Pakhomius', 'Macarius', 'Antonius', 'Cyril', 'Athanasius',
    'Samaan', 'Hany', 'Magdy', 'Fady', 'Remon', 'Romany', 'Sherif', 'Gerges', 'Demian',
    'Abanoub', 'Habib', 'Tawadros', 'Youssef', 'Ehab', 'Maged', 'Sameh', 'Boshra', 'Atef',
]

COPTIC_LAST_NAMES = [
    'Naguib', 'Girgis', 'Hanna', 'Boutros', 'Shawky', 'Fakhry', 'Mansour', 'Attia',
    'Sami', 'Samuel', 'Rafik', 'Kamel', 'Zaky', 'Habib', 'Saad', 'Aziz', 'Yacoub',
    'Fawzy', 'Eskander', 'Naim', 'Tawfik', 'Wasfy', 'Maher', 'Selim', 'Abadeer',
    'Botros', 'Ibrahim', 'Halim', 'Mansy', 'Khalil', 'Asaad', 'Sabry', 'Wahba',
    'Bekhit', 'Ghaly', 'Saleeb', 'Tadros', 'Awad', 'Boulos', 'Ibrahim', 'Kostandy',
]

LOCATIONS = [
    'Main Football Field', 'Indoor Court A', 'Indoor Court B', 'Volleyball Hall',
    'Church Hall', 'Community Center', 'Outdoor Track', 'Field 2',
    'Saint Mary Hall', 'Father Bishoy Hall', 'Youth Center', 'Sports Complex',
]

DEFAULT_PASSWORD = 'pass123'
HASHED_PASSWORD = make_password(DEFAULT_PASSWORD)

# ─── HELPERS ──────────────────────────────────────────────────────────────────

def make_egyptian_name():
    return random.choice(COPTIC_FIRST_NAMES), random.choice(COPTIC_LAST_NAMES)


def random_phone():
    return f"+201{random.choice([0,1,2,5])}{random.randint(10000000, 99999999)}"


def make_user(username, first, last, roles, password=DEFAULT_PASSWORD,
              dob=None, phone=None, address=None, is_super=False):
    """Create user idempotently. Skips if username already exists."""
    if User.objects.filter(username=username).exists():
        return User.objects.get(username=username)
    user = User(
        username=username,
        first_name=first,
        last_name=last,
        email=f'{username}@boyscenter.local',
        roles=roles,
        phone=phone or random_phone(),
        date_of_birth=dob,
        address=address or fake.address().replace('\n', ', '),
        is_active=True,
    )
    user.password = HASHED_PASSWORD if password == DEFAULT_PASSWORD else make_password(password)
    if is_super:
        user.is_staff = True
        user.is_superuser = True
    user.save()
    return user


def with_progress(label, items, fn):
    """Iterate with simple progress output."""
    total = len(items)
    last_pct = -1
    for i, item in enumerate(items, 1):
        fn(item, i)
        pct = i * 100 // total
        if pct >= last_pct + 10:
            sys.stdout.write(f"\r  {label}: {pct}% ({i}/{total})")
            sys.stdout.flush()
            last_pct = pct
    print(f"\r  {label}: ✓ {total} created          ")


# ─── 1. ADMIN + STAFF ─────────────────────────────────────────────────────────

print("\n🌱 Seeding Boys Center demo data...\n")
print("[1/8] Admin & coach manager")

admin = make_user('admin', 'Father', 'Bishoy', [Role.ADMIN], password='admin123', is_super=True)
mgr = make_user('manager', 'George', 'Naguib', [Role.COACH_MANAGER])

print(f"  ✓ Admin: admin / admin123")
print(f"  ✓ Manager: manager / pass123")


# ─── 2. COACHES (one for each sport, plus extras) ─────────────────────────────

print("\n[2/8] Creating coaches")

SPORT_LIST = ['football', 'basketball', 'volleyball', 'handball', 'table_tennis']

coaches = {}
for i, sport in enumerate(SPORT_LIST):
    fn, ln = make_egyptian_name()
    username = f'coach_{sport[:5]}_{i}'
    user = make_user(username, fn, ln, [Role.COACH])
    user.primary_sport = sport
    user.is_servant = (random.random() < 0.3)
    user.save(update_fields=['primary_sport', 'is_servant'])
    coaches[sport] = [user]

# Extra coaches
for i in range(6):
    fn, ln = make_egyptian_name()
    sport = random.choice(SPORT_LIST)
    user = make_user(f'coach_{i+10}', fn, ln, [Role.COACH])
    user.primary_sport = sport
    user.is_servant = (random.random() < 0.3)
    user.save(update_fields=['primary_sport', 'is_servant'])
    coaches[sport].append(user)

all_coaches = [c for clist in coaches.values() for c in clist]
print(f"  ✓ {len(all_coaches)} coaches across {len(SPORT_LIST)} sports")


# ─── 3. PARENTS ───────────────────────────────────────────────────────────────

print("\n[3/8] Creating parents")

NUM_PARENTS = 80
parents = []
for i in range(NUM_PARENTS):
    fn, ln = make_egyptian_name()
    user = make_user(f'parent_{i+1}', fn, ln, [Role.PARENT])
    parents.append(user)

print(f"  ✓ {NUM_PARENTS} parents created")


# ─── 4. YOUTH PLAYERS ─────────────────────────────────────────────────────────

print("\n[4/8] Creating youth members")

NUM_YOUTH = 200
youth_players = []
today = date.today()

def create_youth(_, i):
    fn, ln = make_egyptian_name()
    age = random.randint(8, 18)
    dob = today - timedelta(days=age*365 + random.randint(0, 364))
    user = make_user(f'youth_{i:03d}', fn, ln, [Role.YOUTH], dob=dob)
    youth_players.append(user)

with_progress("Youth", list(range(NUM_YOUTH)), create_youth)


# ─── 5. PARENT-CHILD RELATIONSHIPS ───────────────────────────────────────────

print("\n[5/8] Linking parents to children")

# Each parent has 1-3 children; ~70% of youth have a parent linked.
linkable_youth = list(youth_players)
random.shuffle(linkable_youth)

idx = 0
for parent in parents:
    if idx >= len(linkable_youth):
        break
    children_count = random.choices([1, 2, 3], weights=[55, 35, 10])[0]
    for _ in range(children_count):
        if idx >= len(linkable_youth):
            break
        child = linkable_youth[idx]
        # Use 80% chance to actually link (so some youth have no parent)
        if random.random() < 0.85:
            child.parents.add(parent)
        idx += 1

# Update last_name of some children to match parent for realism
for parent in parents:
    children = parent.children.all()
    for child in children:
        if random.random() < 0.7:
            child.last_name = parent.last_name
            child.save(update_fields=['last_name'])

linked_count = sum(1 for y in youth_players if y.parents.exists())
print(f"  ✓ {linked_count} youth linked to parents")


# ─── 6. TEAMS, COACH ASSIGNMENTS, TRAINING ───────────────────────────────────

print("\n[6/8] Creating teams, matches, training schedules")

AGE_GROUPS = ['U-12', 'U-15', 'U-18']

teams_by_sport = {sport: [] for sport in SPORT_LIST}

for sport in SPORT_LIST:
    for age_group in AGE_GROUPS:
        # 1-2 teams per age group per sport
        num_teams = random.randint(1, 2)
        for tnum in range(num_teams):
            team_name = f"{age_group} {sport.title()} {chr(65 + tnum)}"
            team = Team.objects.create(
                name=team_name,
                sport=sport,
                age_group=age_group,
                coach=random.choice(coaches[sport]),
            )
            # Add 8-15 random youth players that match age range loosely
            members = random.sample(youth_players, k=random.randint(8, 15))
            team.members.set(members)
            teams_by_sport[sport].append(team)

            # Create coach assignment
            ca = CoachAssignment.objects.create(coach=team.coach, sport=sport, team=team)
            ca.players.set(members)

# Training schedules — one per team with day spread
for sport in SPORT_LIST:
    for team in teams_by_sport[sport]:
        TrainingSchedule.objects.create(
            sport=sport,
            team=team,
            coach=team.coach,
            day_of_week=random.randint(0, 6),
            start_time=time(random.randint(15, 18), random.choice([0, 30])),
            end_time=time(random.randint(19, 20), random.choice([0, 30])),
            location=random.choice(LOCATIONS),
        )

total_teams = sum(len(t) for t in teams_by_sport.values())
print(f"  ✓ {total_teams} teams created")


# ─── MATCHES ─────────────────────────────────────────────────────────────────

# For each sport: schedule round-robin with realistic scores
match_count = 0
goals_count = 0
for sport, teams in teams_by_sport.items():
    if len(teams) < 2:
        continue
    # Past matches (last 60 days) — completed
    for _ in range(random.randint(8, 18)):
        home, away = random.sample(teams, 2)
        when = timezone.now() - timedelta(
            days=random.randint(1, 60),
            hours=random.randint(0, 23)
        )
        if sport == 'football':
            hs, as_ = random.randint(0, 5), random.randint(0, 5)
        elif sport == 'basketball':
            hs, as_ = random.randint(40, 95), random.randint(40, 95)
        elif sport == 'volleyball':
            hs, as_ = random.choice([(3, 0), (3, 1), (3, 2), (0, 3), (1, 3), (2, 3)])
        elif sport == 'handball':
            hs, as_ = random.randint(15, 35), random.randint(15, 35)
        else:  # table_tennis
            hs, as_ = random.choice([(3, 0), (3, 1), (3, 2), (0, 3), (1, 3), (2, 3)])

        match = Match.objects.create(
            sport=sport, home_team=home, away_team=away,
            scheduled_at=when, location=random.choice(LOCATIONS),
            home_score=hs, away_score=as_, is_completed=True,
        )
        match_count += 1

        # Generate goal records (only football for now since GoalRecord makes most sense there)
        if sport == 'football':
            for team_obj, score_value in [(home, hs), (away, as_)]:
                if not team_obj.members.exists():
                    continue
                for _g in range(score_value):
                    scorer = random.choice(list(team_obj.members.all()))
                    GoalRecord.objects.create(
                        match=match, player=scorer, team=team_obj,
                        minute=random.randint(1, 90), points=1,
                    )
                    goals_count += 1
        elif sport == 'basketball':
            # Sample basketball points (each event is 2 or 3 pts)
            for team_obj, score_value in [(home, hs), (away, as_)]:
                if not team_obj.members.exists():
                    continue
                remaining = score_value
                while remaining > 0:
                    pts = random.choice([2, 2, 2, 3])
                    if pts > remaining:
                        pts = remaining
                    scorer = random.choice(list(team_obj.members.all()))
                    GoalRecord.objects.create(
                        match=match, player=scorer, team=team_obj,
                        points=pts,
                    )
                    remaining -= pts
                    goals_count += 1

    # Future matches — upcoming
    for _ in range(random.randint(3, 7)):
        home, away = random.sample(teams, 2)
        when = timezone.now() + timedelta(
            days=random.randint(1, 30),
            hours=random.randint(0, 23),
        )
        Match.objects.create(
            sport=sport, home_team=home, away_team=away,
            scheduled_at=when, location=random.choice(LOCATIONS),
            is_completed=False,
        )
        match_count += 1

print(f"  ✓ {match_count} matches scheduled, {goals_count} goal records")


# ─── 7. ATTENDANCE SESSIONS + RECORDS ────────────────────────────────────────

print("\n[7/8] Generating attendance sessions and records")

NUM_SESSIONS = 60
sessions = []
session_titles = [
    'Football Training', 'Basketball Practice', 'Volleyball Drill',
    'Friday Prayer Meeting', 'Sunday Bible Study', 'Sports Festival',
    'Youth Spiritual Retreat', 'Open Gym Session',
]

for i in range(NUM_SESSIONS):
    days_ago = random.randint(0, 60)
    sdate = today - timedelta(days=days_ago)
    sport = random.choice(SPORT_LIST)
    coach = random.choice(coaches[sport])
    title = f"{random.choice(session_titles)} – {sdate.strftime('%b %d')}"
    stype = random.choices(
        [SessionType.TRAINING, SessionType.PRAYER, SessionType.MATCH, SessionType.EVENT],
        weights=[60, 20, 12, 8]
    )[0]
    s = AttendanceSession.objects.create(
        title=title,
        session_type=stype,
        sport=sport if stype == SessionType.TRAINING else '',
        coach=coach,
        date=sdate,
        start_time=time(random.choice([15, 16, 17, 18]), random.choice([0, 30])),
        end_time=time(random.choice([19, 20]), random.choice([0, 30])),
        location=random.choice(LOCATIONS),
        is_open=days_ago < 1,  # only today's are open
    )
    sessions.append(s)

# Generate attendance records — ~70% attendance rate per session, prefer team members
def populate_records(session, idx):
    # Pick relevant players: if session has a sport, prefer members of teams in that sport
    if session.sport:
        candidate_players = list({m for t in teams_by_sport[session.sport] for m in t.members.all()})
    else:
        candidate_players = list(youth_players)
    if not candidate_players:
        return
    sample_size = min(int(len(candidate_players) * random.uniform(0.4, 0.85)), 40)
    attending = random.sample(candidate_players, k=sample_size)

    session_dt = timezone.make_aware(datetime.combine(session.date, session.start_time))
    for player in attending:
        # 80% present, 15% late, 5% excused
        status = random.choices(['present', 'late', 'excused'], weights=[78, 17, 5])[0]
        offset_min = random.randint(-10, 5) if status == 'present' else random.randint(20, 60)
        AttendanceRecord.objects.create(
            session=session, user=player,
            status=status,
            check_in_time=session_dt + timedelta(minutes=offset_min),
        )

with_progress("Attendance", sessions, populate_records)


# ─── 8. EVALUATIONS, NEWS, EVENTS ────────────────────────────────────────────

print("\n[8/8] Creating evaluations, news, and events")

# Evaluations — about 3-5 per youth from various coaches
eval_count = 0
for youth in youth_players[:120]:  # not every youth needs evals — leave a few empty
    n_evals = random.randint(1, 5)
    for _ in range(n_evals):
        coach = random.choice(all_coaches)
        days_ago = random.randint(0, 90)
        Evaluation.objects.create(
            coach=coach, player=youth,
            sport=random.choice(SPORT_LIST),
            performance=random.randint(2, 5),
            behavior=random.randint(3, 5),
            commitment=random.randint(2, 5),
            notes=fake.sentence(nb_words=random.randint(8, 20)) if random.random() < 0.5 else '',
            created_at=timezone.now() - timedelta(days=days_ago),
        )
        eval_count += 1
print(f"  ✓ {eval_count} evaluations created")


# News posts
NEWS_TEMPLATES = [
    ("Summer Camp Registration Open!", "تسجيل مخيم الصيف مفتوح!",
     "Registration for the Boys Center Summer Camp is now open. Join us for a week of sports, faith, and fellowship.",
     "التسجيل في مخيم البويز سنتر الصيفي مفتوح الآن. انضم إلينا لأسبوع من الرياضة والإيمان والشركة.", True),
    ("Eagles FC win the regional cup!", "نسور الكنيسة يفوزون بالكأس الإقليمية!",
     "Massive congratulations to our U-15 football team for clinching the regional youth cup last weekend.",
     "تهانينا الحارة لفريق كرة قدم الناشئين على فوزه بكأس الناشئين الإقليمية الأسبوع الماضي.", True),
    ("New Basketball Court Now Open", "ملعب كرة السلة الجديد جاهز",
     "We are excited to announce that our new indoor basketball court is now open. Schedule below.",
     "يسعدنا الإعلان عن افتتاح ملعب كرة السلة الداخلي الجديد.", False),
    ("Father Marcos Visiting This Sunday", "زيارة الأب مرقس يوم الأحد",
     "Father Marcos will be joining us this Sunday for a special talk on faith and youth ministry.",
     "سيشاركنا الأب مرقس يوم الأحد في حديث خاص عن الإيمان وخدمة الشباب.", False),
    ("Volleyball Season Starting Soon", "موسم كرة الطائرة قريباً",
     "Tryouts for the new volleyball season begin next Monday. All ages welcome to participate.",
     "تبدأ اختبارات موسم كرة الطائرة الجديد يوم الإثنين.", False),
    ("Annual Sports Day Recap", "ملخص اليوم الرياضي السنوي",
     "What a day! Over 200 youth participated in our annual sports day. Thank you to all parents and volunteers.",
     "يوم رائع! شارك أكثر من 200 شاب في يومنا الرياضي السنوي.", False),
    ("Christmas Service Schedule", "جدول خدمات عيد الميلاد",
     "Please find the schedule for our Christmas services and youth events below.",
     "تجدوا أدناه جدول خدمات وأنشطة عيد الميلاد.", False),
    ("New Coaches Welcome", "ترحيب بالمدربين الجدد",
     "We're delighted to welcome two new coaches joining our basketball and volleyball programs.",
     "يسعدنا الترحيب بمدربين جديدين ينضمان لبرامج كرة السلة والطائرة.", False),
    ("Parent-Coach Meeting Reminder", "تذكير اجتماع الآباء والمدربين",
     "Friendly reminder: parent-coach quarterly meeting takes place this Saturday at 10 AM.",
     "تذكير: اجتماع الآباء والمدربين الفصلي يوم السبت الساعة العاشرة.", False),
    ("Upcoming Holy Week Activities", "أنشطة أسبوع الآلام القادمة",
     "All youth are invited to join the special Holy Week activities and prayer meetings.",
     "جميع الشباب مدعوون للمشاركة في أنشطة وصلوات أسبوع الآلام.", True),
]

for i, (title, t_ar, content, c_ar, is_featured) in enumerate(NEWS_TEMPLATES):
    NewsPost.objects.create(
        title=title, title_ar=t_ar,
        excerpt=content[:120],
        content=content + "\n\n" + fake.paragraph(nb_sentences=5),
        content_ar=c_ar,
        author=admin if i % 2 == 0 else mgr,
        is_published=True,
        is_featured=is_featured,
        created_at=timezone.now() - timedelta(days=random.randint(0, 30))
    )
print(f"  ✓ {len(NEWS_TEMPLATES)} news posts created")


# Events
EVENT_TEMPLATES = [
    ("U-15 Football vs Saint George Eagles", EventType.MATCH, 3, 16, 18),
    ("Friday Evening Prayer Meeting", EventType.PRAYER, 2, 18, 20),
    ("Basketball Training Session", EventType.TRAINING, 4, 17, 19),
    ("Parent-Child Bible Quiz", EventType.PARENT, 6, 15, 17),
    ("Annual Spring Camp", EventType.CAMP, 21, 9, 18),
    ("Sunday Volleyball Practice", EventType.TRAINING, 5, 16, 18),
    ("Mother's Day Gathering", EventType.PARENT, 14, 14, 17),
    ("U-18 Football vs Anba Bishoy", EventType.MATCH, 10, 19, 21),
    ("Youth Choir Practice", EventType.OTHER, 3, 17, 19),
    ("Liturgy Service", EventType.PRAYER, 7, 8, 11),
    ("Handball Tournament Opening", EventType.MATCH, 12, 14, 18),
    ("End-of-Term Celebration", EventType.OTHER, 25, 17, 21),
    ("Summer Camp Day 1", EventType.CAMP, 30, 8, 22),
    ("Summer Camp Day 2", EventType.CAMP, 31, 8, 22),
    ("Family Picnic Day", EventType.PARENT, 9, 10, 18),
]

for title, etype, days, sh, eh in EVENT_TEMPLATES:
    start_dt = timezone.now() + timedelta(days=days)
    start_dt = start_dt.replace(hour=sh, minute=0, second=0, microsecond=0)
    end_dt = start_dt.replace(hour=eh, minute=0)
    Event.objects.create(
        title=title, event_type=etype,
        description=fake.paragraph(nb_sentences=3),
        start_datetime=start_dt, end_datetime=end_dt,
        location=random.choice(LOCATIONS),
        created_by=admin,
    )

# Add some past events too
for i in range(8):
    start_dt = timezone.now() - timedelta(days=random.randint(1, 60))
    Event.objects.create(
        title=fake.sentence(nb_words=5).rstrip('.'),
        event_type=random.choice([e.value for e in EventType]),
        description=fake.paragraph(),
        start_datetime=start_dt, end_datetime=start_dt + timedelta(hours=2),
        location=random.choice(LOCATIONS),
        created_by=admin,
    )
print(f"  ✓ {len(EVENT_TEMPLATES) + 8} events created")


# Activity log entries
for _ in range(40):
    user = random.choice(youth_players + parents + all_coaches)
    ActivityLog.objects.create(
        user=user,
        action=random.choice(['user_login', 'self_checkin', 'profile_viewed',
                             'evaluation_created', 'session_created']),
        ip_address=fake.ipv4(),
        timestamp=timezone.now() - timedelta(hours=random.randint(0, 240)),
    )


# ─── SUMMARY ──────────────────────────────────────────────────────────────────

print("\n" + "═" * 56)
print("✓ SEED COMPLETE\n")
print(f"  Total users:        {User.objects.count()}")
print(f"  Youth members:      {NUM_YOUTH}")
print(f"  Parents:            {NUM_PARENTS}")
print(f"  Coaches:            {len(all_coaches)}")
print(f"  Teams:              {Team.objects.count()}")
print(f"  Matches:            {Match.objects.count()}")
print(f"  Goal records:       {GoalRecord.objects.count()}")
print(f"  Sessions:           {AttendanceSession.objects.count()}")
print(f"  Attendance records: {AttendanceRecord.objects.count()}")
print(f"  Evaluations:        {Evaluation.objects.count()}")
print(f"  News posts:         {NewsPost.objects.count()}")
print(f"  Events:             {Event.objects.count()}")
print("═" * 56)
print("\n🔐 LOGIN CREDENTIALS")
print("  Admin     : admin / admin123")
print("  Manager   : manager / pass123")
print(f"  Coach     : coach_footb_0 / pass123")
print(f"  Parent    : parent_1 / pass123")
print(f"  Youth     : youth_001 / pass123")
print()
