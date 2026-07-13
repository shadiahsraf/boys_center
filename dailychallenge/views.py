"""
Daily Challenge views.

Solver flow:
  GET  /challenge/            -> today's quiz (or a preview for staff via ?date=)
  POST /challenge/submit/     -> grade answers, update streak, redirect to results

Management flow (admin / coach-manager only):
  GET  /challenge/manage/                 -> list of all DailyContent
  GET  /challenge/manage/new/             -> create form
  POST /challenge/manage/new/             -> create handler
  GET  /challenge/manage/<id>/edit/       -> edit form (prefilled)
  POST /challenge/manage/<id>/edit/       -> update handler
  POST /challenge/manage/<id>/delete/     -> delete handler
"""
from datetime import date as date_cls, datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView, ListView

from users.mixins import RoleRequiredMixin
from users.models import Role
from .models import DailyContent, Question, Choice, ChallengeProgress, ChallengeAnswer


QUESTIONS_PER_CONTENT = 3
CHOICES_PER_QUESTION = 4
HISTORY_DAYS = 7

# Short Arabic day labels (Mon=0 .. Sun=6)
ARABIC_DAY_SHORT = ['إث', 'ث', 'أر', 'خ', 'ج', 'س', 'ح']

# Reward verses shown after completion — rotates daily.
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
    ('افرحوا في الرب كل حين.', 'فيلبي 4:4'),
]


def _get_history(user, days=HISTORY_DAYS, today=None):
    """Last N days' completion status for the streak calendar."""
    today = today or date_cls.today()
    start = today - timedelta(days=days - 1)
    counts = (
        ChallengeAnswer.objects
        .filter(user=user, daily_content__date__gte=start,
                daily_content__date__lte=today)
        .values('daily_content__date')
        .annotate(c=Count('id'))
    )
    by_day = {row['daily_content__date']: row['c'] for row in counts}
    out = []
    for i in range(days):
        d = start + timedelta(days=i)
        cnt = by_day.get(d, 0)
        out.append({
            'date': d.isoformat(),
            'short_label': ARABIC_DAY_SHORT[d.weekday()],
            'day_of_month': d.day,
            'complete': cnt >= QUESTIONS_PER_CONTENT,
            'partial': 0 < cnt < QUESTIONS_PER_CONTENT,
            'is_today': (d == today),
        })
    return out


def _get_reward_verse(today=None):
    today = today or date_cls.today()
    text, ref = REWARD_VERSES[today.toordinal() % len(REWARD_VERSES)]
    return {'text': text, 'reference': ref}


def _get_progress(user):
    progress, _created = ChallengeProgress.objects.get_or_create(user=user)
    return progress


class DailyChallengeView(LoginRequiredMixin, TemplateView):
    template_name = 'dailychallenge/today.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        today = date_cls.today()

        # Staff may preview any date via ?date=YYYY-MM-DD (read-only, no streak effect)
        target = today
        preview = False
        date_str = self.request.GET.get('date')
        if date_str and user.is_staff:
            try:
                target = datetime.strptime(date_str, '%Y-%m-%d').date()
                preview = (target != today)
            except ValueError:
                target = today

        content = (DailyContent.objects
                   .filter(date=target, is_published=True)
                   .prefetch_related('questions__choices')
                   .first())

        progress = _get_progress(user)

        # Existing answers for this content (so completed days show results)
        answers = {}
        if content:
            answers = {
                a.question_id: a
                for a in ChallengeAnswer.objects.filter(user=user, daily_content=content)
            }

        total_questions = content.questions.count() if content else 0
        completed = bool(answers) and len(answers) >= total_questions and total_questions > 0

        # Only YOUTH members can solve. Everyone else (admin / coach / manager)
        # sees the page in read-only "review" mode with the answers revealed.
        is_solver = user.is_youth
        review_mode = (content is not None) and (not is_solver) and (not preview)

        # Reveal correct answers when: completed, staff preview, or review mode
        reveal = completed or preview or review_mode

        letters = ['A', 'B', 'C', 'D', 'E', 'F']
        questions = []
        if content:
            for q in content.questions.all():
                a = answers.get(q.id)
                correct = q.correct_choice
                choice_list = []
                for i, ch in enumerate(q.choices.all()):
                    choice_list.append({
                        'id': ch.id,
                        'text': ch.text,
                        'letter': letters[i] if i < len(letters) else str(i + 1),
                    })
                questions.append({
                    'q': q,
                    'choices': choice_list,
                    'answered': bool(a),
                    'selected_id': a.selected_choice_id if a else None,
                    'is_correct': a.is_correct if a else None,
                    'correct_id': correct.id if (reveal and correct) else None,
                })

        # Answerable only for: a YOUTH member, today's content, not preview, not done
        answerable = (
            content is not None
            and is_solver
            and (target == today)
            and (not completed)
            and (not preview)
        )
        correct_count = sum(1 for a in answers.values() if a.is_correct)

        ctx.update({
            'content': content,
            'questions': questions,
            'completed': completed,
            'answerable': answerable,
            'reveal': reveal,
            'preview': preview,
            'review_mode': review_mode,
            'is_solver': is_solver,
            'is_today': (target == today),
            'target_date': target,
            'correct_count': correct_count,
            'total_questions': total_questions,
            'progress': progress,
            'streak': progress.effective_streak,
            'history': _get_history(user, today=today),
            'reward_verse': _get_reward_verse(today),
        })
        return ctx


@login_required
@require_POST
def submit_challenge(request):
    # Only youth members may solve the daily challenge.
    if not request.user.is_youth:
        messages.error(request, _('Only youth members can answer the daily challenge.'))
        return redirect('dailychallenge:today')

    today = date_cls.today()
    content = (DailyContent.objects
               .filter(date=today, is_published=True)
               .prefetch_related('questions__choices')
               .first())

    if not content:
        messages.error(request, _('No challenge is available for today.'))
        return redirect('dailychallenge:today')

    progress = _get_progress(request.user)

    # Idempotent: if already completed today, just show the results
    if ChallengeAnswer.objects.filter(user=request.user, daily_content=content).exists():
        return redirect('dailychallenge:today')

    for q in content.questions.all():
        raw = request.POST.get(f'q_{q.id}')
        selected = q.choices.filter(id=raw).first() if raw else None
        is_correct = bool(selected and selected.is_correct)
        ChallengeAnswer.objects.update_or_create(
            user=request.user, question=q,
            defaults={
                'daily_content': content,
                'selected_choice': selected,
                'is_correct': is_correct,
            },
        )

    # Update streak (consecutive day -> +1, otherwise reset to 1)
    progress.record_completion(today)
    messages.success(request, _('Daily challenge completed! Your streak is updated.'))
    return redirect('dailychallenge:today')


# ═══════════════════════════════════════════════════════════════════════════
# MANAGEMENT VIEWS (admin / coach-manager only)
# ═══════════════════════════════════════════════════════════════════════════

class ManageMixin(RoleRequiredMixin):
    """Restricts access to staff content managers."""
    required_roles = [Role.ADMIN, Role.COACH_MANAGER]


class ManageListView(ManageMixin, ListView):
    """All DailyContent entries with status pills + edit/delete actions."""
    template_name = 'dailychallenge/manage_list.html'
    context_object_name = 'items'
    paginate_by = 30

    def get_queryset(self):
        return (DailyContent.objects
                .annotate(qcount=Count('questions'))
                .order_by('-date'))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = date_cls.today()
        ctx['today'] = today
        ctx['tomorrow'] = today + timedelta(days=1)
        ctx['has_today']    = DailyContent.objects.filter(date=today).exists()
        ctx['has_tomorrow'] = DailyContent.objects.filter(date=today + timedelta(days=1)).exists()
        ctx['total']        = DailyContent.objects.count()
        ctx['published']    = DailyContent.objects.filter(is_published=True).count()
        return ctx


def _build_form_state(content: DailyContent | None = None, post_data: dict | None = None):
    """
    Build the per-question/per-choice values used by the create+edit template
    so the same template handles both fresh & validation-error renders.
    """
    state = {
        'date': '',
        'bible_reference': '',
        'is_published': True,
        'questions': [],
        'errors': {},
    }

    letters = ['A', 'B', 'C', 'D']

    if post_data is not None:
        state['date'] = post_data.get('date', '').strip()
        state['bible_reference'] = post_data.get('bible_reference', '').strip()
        state['is_published'] = bool(post_data.get('is_published'))
        for qi in range(QUESTIONS_PER_CONTENT):
            qdata = {
                'index': qi,
                'number': qi + 1,
                'text': post_data.get(f'q{qi}_text', '').strip(),
                'correct': post_data.get(f'q{qi}_correct', ''),
                'choices': [
                    {
                        'index': ci, 'letter': letters[ci],
                        'text': post_data.get(f'q{qi}_c{ci}', '').strip(),
                        'is_chosen': post_data.get(f'q{qi}_correct') == str(ci),
                        'error': '',
                    }
                    for ci in range(CHOICES_PER_QUESTION)
                ],
                'text_error': '', 'correct_error': '',
            }
            state['questions'].append(qdata)
        return state

    if content is not None:
        state['date'] = content.date.isoformat()
        state['bible_reference'] = content.bible_reference
        state['is_published'] = content.is_published
        existing_qs = list(content.questions.all()[:QUESTIONS_PER_CONTENT])
        for qi in range(QUESTIONS_PER_CONTENT):
            q = existing_qs[qi] if qi < len(existing_qs) else None
            choices = list(q.choices.all()[:CHOICES_PER_QUESTION]) if q else []
            correct_idx = ''
            choice_list = []
            for ci in range(CHOICES_PER_QUESTION):
                ch = choices[ci] if ci < len(choices) else None
                if ch and ch.is_correct:
                    correct_idx = str(ci)
                choice_list.append({
                    'index': ci, 'letter': letters[ci],
                    'text': ch.text if ch else '',
                    'is_chosen': bool(ch and ch.is_correct),
                    'error': '',
                })
            state['questions'].append({
                'index': qi, 'number': qi + 1,
                'text': q.text if q else '',
                'correct': correct_idx,
                'choices': choice_list,
                'text_error': '', 'correct_error': '',
            })
        return state

    # Fresh form — default to tomorrow's date
    state['date'] = (date_cls.today() + timedelta(days=1)).isoformat()
    for qi in range(QUESTIONS_PER_CONTENT):
        state['questions'].append({
            'index': qi, 'number': qi + 1,
            'text': '', 'correct': '',
            'choices': [
                {'index': ci, 'letter': letters[ci], 'text': '',
                 'is_chosen': False, 'error': ''}
                for ci in range(CHOICES_PER_QUESTION)
            ],
            'text_error': '', 'correct_error': '',
        })
    return state


def _validate_state(state, *, editing_pk=None):
    """
    Returns top-level errors dict {date, bible_reference} and attaches
    per-question errors directly to state['questions'][i] so the template
    can render them without custom template filters.
    """
    errors = {}

    # Date
    raw_date = state['date']
    parsed_date = None
    if not raw_date:
        errors['date'] = _('Date is required.')
    else:
        try:
            parsed_date = datetime.strptime(raw_date, '%Y-%m-%d').date()
        except ValueError:
            errors['date'] = _('Invalid date — use the picker.')
    state['parsed_date'] = parsed_date

    if parsed_date is not None:
        qs = DailyContent.objects.filter(date=parsed_date)
        if editing_pk:
            qs = qs.exclude(pk=editing_pk)
        if qs.exists():
            errors['date'] = _('Another challenge already exists for this date.')

    if not state['bible_reference']:
        errors['bible_reference'] = _('Bible reference is required.')

    has_q_errors = False
    for q in state['questions']:
        q['text_error'] = ''
        q['correct_error'] = ''
        if not q['text']:
            q['text_error'] = _('Question text is required.')
            has_q_errors = True
        for ch in q['choices']:
            ch['error'] = ''
            if not ch['text']:
                ch['error'] = _('Required.')
                has_q_errors = True
        if q['correct'] not in ('0', '1', '2', '3'):
            q['correct_error'] = _('Pick the correct answer.')
            has_q_errors = True

    if has_q_errors:
        errors['_questions'] = True
    return errors


@transaction.atomic
def _save_state(state, *, content: DailyContent | None = None) -> DailyContent:
    """Creates or replaces the content + questions + choices."""
    if content is None:
        content = DailyContent.objects.create(
            date=state['parsed_date'],
            bible_reference=state['bible_reference'],
            is_published=state['is_published'],
        )
    else:
        content.date = state['parsed_date']
        content.bible_reference = state['bible_reference']
        content.is_published = state['is_published']
        content.save()
        # Clean slate — wipe existing questions, choices, and any user attempts
        content.questions.all().delete()
        content.answers.all().delete()

    for qi, qdata in enumerate(state['questions']):
        q = Question.objects.create(
            daily_content=content, text=qdata['text'], order=qi + 1,
        )
        correct_idx = int(qdata['correct'])
        for ci, ch in enumerate(qdata['choices']):
            Choice.objects.create(
                question=q, text=ch['text'], is_correct=(ci == correct_idx),
            )
    return content


class ManageCreateView(ManageMixin, View):
    template_name = 'dailychallenge/manage_form.html'

    def get(self, request):
        state = _build_form_state()
        return render(request, self.template_name, {
            'state': state, 'mode': 'create', 'errors': {}, 'content': None,
        })

    def post(self, request):
        state = _build_form_state(post_data=request.POST)
        errors = _validate_state(state)
        if errors:
            return render(request, self.template_name, {
                'state': state, 'errors': errors,
                'mode': 'create', 'content': None,
            })
        content = _save_state(state)
        messages.success(request, _('Daily challenge created for %(d)s.') % {'d': content.date})
        return redirect('dailychallenge:manage_list')


class ManageUpdateView(ManageMixin, View):
    template_name = 'dailychallenge/manage_form.html'

    def get_object(self, pk):
        return get_object_or_404(DailyContent, pk=pk)

    def get(self, request, pk):
        content = self.get_object(pk)
        state = _build_form_state(content=content)
        return render(request, self.template_name, {
            'state': state, 'mode': 'edit', 'errors': {}, 'content': content,
        })

    def post(self, request, pk):
        content = self.get_object(pk)
        state = _build_form_state(post_data=request.POST)
        errors = _validate_state(state, editing_pk=content.pk)
        if errors:
            return render(request, self.template_name, {
                'state': state, 'errors': errors,
                'mode': 'edit', 'content': content,
            })
        _save_state(state, content=content)
        messages.success(request, _('Daily challenge updated.'))
        return redirect('dailychallenge:manage_list')


class ManageDeleteView(ManageMixin, View):
    template_name = 'dailychallenge/manage_confirm_delete.html'

    def get(self, request, pk):
        content = get_object_or_404(DailyContent, pk=pk)
        return render(request, self.template_name, {'content': content})

    def post(self, request, pk):
        content = get_object_or_404(DailyContent, pk=pk)
        d = content.date
        content.delete()
        messages.success(request, _('Daily challenge for %(d)s was deleted.') % {'d': d})
        return redirect('dailychallenge:manage_list')
