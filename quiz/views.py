"""
Daily Bible quiz — 3 questions per user per day, instant feedback, streak system.

The 3 questions for a given (user, day) are selected deterministically (same set
shown on refresh) and exclude anything the user has answered in the last 30 days.
"""
import hashlib
import json
import random
from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

from .models import BibleQuestion, DailyQuizAttempt, UserStreak


QUESTIONS_PER_DAY = 3
RECENT_WINDOW_DAYS = 30  # don't repeat questions within this window
HISTORY_DAYS = 7         # mini calendar size

# Short Arabic day labels — Python weekday(): 0=Mon ... 6=Sun
ARABIC_DAY_SHORT = ['إث', 'ث', 'أر', 'خ', 'ج', 'س', 'ح']

# Small pool of reward verses — pick one deterministically per day.
REWARD_VERSES = [
    ('النور يضيء في الظلمة، والظلمة لم تدركه.', 'يوحنا 1:5'),
    ('الرب راعيَّ فلا يعوزني شيء.', 'مزمور 23:1'),
    ('أستطيع كل شيء في المسيح الذي يقويني.', 'فيلبي 4:13'),
    ('كل شيء مستطاع للمؤمن.', 'مرقس 9:23'),
    ('محبة الرب إلى الأبد.', 'مزمور 100:5'),
    ('كونوا مستعدين في كل حين.', '1 بطرس 3:15'),
    ('تعالوا إليّ يا جميع المتعَبين وأنا أريحكم.', 'متى 11:28'),
    ('صلّوا بلا انقطاع.', '1 تسالونيكي 5:17'),
    ('أنتم نور العالم.', 'متى 5:14'),
    ('فرحوا في الرب كل حين.', 'فيلبي 4:4'),
]


def _seeded_rng(user_id, day):
    seed_str = f'{user_id}-{day.isoformat()}'
    seed = int(hashlib.sha256(seed_str.encode()).hexdigest()[:12], 16)
    return random.Random(seed)


def get_daily_questions(user, day=None):
    """Returns the 3 questions for this user on this day. Deterministic."""
    day = day or date.today()
    cutoff = day - timedelta(days=RECENT_WINDOW_DAYS)
    recently_answered_ids = set(DailyQuizAttempt.objects.filter(
        user=user,
        day__gte=cutoff,
        day__lt=day,
    ).values_list('question_id', flat=True))

    pool = list(
        BibleQuestion.objects.filter(is_active=True)
        .exclude(id__in=recently_answered_ids)
        .order_by('id')
    )
    if len(pool) < QUESTIONS_PER_DAY:
        pool = list(BibleQuestion.objects.filter(is_active=True).order_by('id'))

    rng = _seeded_rng(user.pk, day)
    rng.shuffle(pool)
    return pool[:QUESTIONS_PER_DAY]


def get_or_create_streak(user):
    streak, _ = UserStreak.objects.get_or_create(user=user)
    return streak


def get_streak_history(user, days=HISTORY_DAYS, today=None):
    """Return last `days` of completion status, oldest first."""
    today = today or date.today()
    start = today - timedelta(days=days - 1)
    counts = (
        DailyQuizAttempt.objects
        .filter(user=user, day__gte=start, day__lte=today)
        .values('day')
        .annotate(count=Count('id'))
    )
    by_day = {c['day']: c['count'] for c in counts}
    history = []
    for i in range(days):
        d = start + timedelta(days=i)
        cnt = by_day.get(d, 0)
        history.append({
            'date': d.isoformat(),
            'short_label': ARABIC_DAY_SHORT[d.weekday()],
            'day_of_month': d.day,
            'complete': cnt >= QUESTIONS_PER_DAY,
            'partial': 0 < cnt < QUESTIONS_PER_DAY,
            'is_today': (d == today),
            'is_future': False,
        })
    return history


def get_reward_verse(today=None):
    """Deterministic verse-of-the-day based on the ordinal date."""
    today = today or date.today()
    idx = today.toordinal() % len(REWARD_VERSES)
    text, ref = REWARD_VERSES[idx]
    return {'text': text, 'reference': ref}


class QuizDayView(LoginRequiredMixin, TemplateView):
    template_name = 'quiz/today.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        today = date.today()
        questions = get_daily_questions(user, today)

        existing = {
            a.question_id: a
            for a in DailyQuizAttempt.objects.filter(user=user, day=today,
                                                     question__in=questions)
        }

        # Build clean JSON-serializable items for Alpine.js (avoids fragile
        # template-side JS escaping with Arabic strings).
        items_json = []
        for q in questions:
            attempt = existing.get(q.id)
            items_json.append({
                'id': q.id,
                'text': q.text,
                'options': [
                    {'letter': 'a', 'text': q.option_a},
                    {'letter': 'b', 'text': q.option_b},
                    {'letter': 'c', 'text': q.option_c},
                    {'letter': 'd', 'text': q.option_d},
                ],
                'reference': q.reference or '',
                'answered': bool(attempt),
                'chosen':   attempt.answer if attempt else None,
                'correct':  q.correct if attempt else None,
                'isCorrect': attempt.is_correct if attempt else None,
            })

        all_done = (len(existing) >= QUESTIONS_PER_DAY)
        correct_today = sum(1 for a in existing.values() if a.is_correct)
        streak = get_or_create_streak(user)
        history = get_streak_history(user, today=today)
        verse = get_reward_verse(today)

        ctx.update({
            'items_json': items_json,
            'state_json': {
                'items': items_json,
                'streakCurrent': streak.effective_streak,
                'streakBest':    streak.best_streak,
                'totalDays':     streak.total_days_completed,
                'correctToday':  correct_today,
                'allDone':       all_done,
                'history':       history,
                'verse':         verse,
                'questionsPerDay': QUESTIONS_PER_DAY,
            },
            'all_done': all_done,
            'correct_today': correct_today,
            'questions_per_day': QUESTIONS_PER_DAY,
            'streak': streak,
        })
        return ctx


@login_required
@require_POST
def submit_answer(request):
    """JSON endpoint — user submits one answer for one question."""
    try:
        data = json.loads(request.body or '{}')
    except ValueError:
        return HttpResponseBadRequest('invalid json')

    question_id = data.get('question_id')
    answer = (data.get('answer') or '').strip().lower()

    if answer not in ('a', 'b', 'c', 'd'):
        return JsonResponse({'ok': False, 'error': 'invalid_answer'}, status=400)

    today = date.today()
    todays_questions = get_daily_questions(request.user, today)
    todays_ids = {q.id for q in todays_questions}
    try:
        qid_int = int(question_id)
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'error': 'invalid_question_id'}, status=400)
    if qid_int not in todays_ids:
        return JsonResponse({'ok': False, 'error': 'question_not_in_today_set'}, status=400)

    question = get_object_or_404(BibleQuestion, pk=qid_int)

    # Idempotent: if attempt exists, return the existing result
    attempt, _ = DailyQuizAttempt.objects.get_or_create(
        user=request.user, question=question, day=today,
        defaults={'answer': answer, 'is_correct': (answer == question.correct)},
    )
    is_correct = attempt.is_correct

    today_attempts = DailyQuizAttempt.objects.filter(user=request.user, day=today)
    completed_count = today_attempts.count()
    correct_today = today_attempts.filter(is_correct=True).count()
    day_complete = completed_count >= QUESTIONS_PER_DAY

    streak = get_or_create_streak(request.user)
    if day_complete:
        streak.record_completion(today)

    return JsonResponse({
        'ok': True,
        'is_correct': is_correct,
        'correct_letter': question.correct,
        'correct_text': question.correct_text,
        'day_complete': day_complete,
        'completed_count': completed_count,
        'correct_today': correct_today,
        'streak_current': streak.effective_streak,
        'streak_best': streak.best_streak,
    })
