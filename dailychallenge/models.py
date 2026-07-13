"""
Daily Bible Quiz — admin-controlled.

An admin curates one `DailyContent` per calendar date (a Bible reference + a
few questions). Youth users answer the questions for *today* only and build a
daily streak.

This app is self-contained and does NOT modify the existing User model: the
per-user streak lives in `ChallengeProgress` (OneToOne link to the user).
"""
from datetime import date, timedelta

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class DailyContent(models.Model):
    """One day's challenge — a Bible reference plus its questions."""
    date = models.DateField(_('Date'), unique=True)
    bible_reference = models.CharField(
        _('Bible reference'), max_length=120,
        help_text=_('Reference only, e.g. "John 15:1-8" — the text is not shown.'),
    )
    is_published = models.BooleanField(_('Published'), default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        verbose_name = _('Daily content')
        verbose_name_plural = _('Daily content')

    def __str__(self):
        return f'{self.date} · {self.bible_reference}'

    @property
    def question_count(self):
        return self.questions.count()


class Question(models.Model):
    daily_content = models.ForeignKey(
        DailyContent, on_delete=models.CASCADE,
        related_name='questions', verbose_name=_('Daily content'),
    )
    text = models.CharField(_('Question'), max_length=400)
    order = models.PositiveIntegerField(_('Order'), default=0)

    class Meta:
        ordering = ['order', 'id']
        verbose_name = _('Question')
        verbose_name_plural = _('Questions')

    def __str__(self):
        return self.text[:60]

    @property
    def correct_choice(self):
        return self.choices.filter(is_correct=True).first()


class Choice(models.Model):
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE,
        related_name='choices', verbose_name=_('Question'),
    )
    text = models.CharField(_('Choice'), max_length=200)
    is_correct = models.BooleanField(_('Correct answer'), default=False)

    class Meta:
        verbose_name = _('Choice')
        verbose_name_plural = _('Choices')

    def __str__(self):
        return self.text[:50]


class ChallengeProgress(models.Model):
    """
    Per-user streak tracker (linked to the existing User via OneToOne — no
    migration on the users app, fully modular).
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='challenge_progress',
    )
    last_completed_date = models.DateField(null=True, blank=True)
    streak_count = models.PositiveIntegerField(default=0)
    best_streak = models.PositiveIntegerField(default=0)
    total_completed = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Challenge progress')
        verbose_name_plural = _('Challenge progress')

    def __str__(self):
        return f'{self.user_id}: streak={self.streak_count}'

    @property
    def effective_streak(self) -> int:
        """0 if the chain is broken (last completion older than yesterday)."""
        if not self.last_completed_date:
            return 0
        if (date.today() - self.last_completed_date).days <= 1:
            return self.streak_count
        return 0

    def record_completion(self, day: date | None = None):
        """Call when the user finishes today's quiz."""
        day = day or date.today()
        if self.last_completed_date == day:
            return  # already counted today
        if self.last_completed_date == day - timedelta(days=1):
            self.streak_count += 1          # consecutive day -> +1
        else:
            self.streak_count = 1           # first time, or chain broken -> reset to 1
        self.last_completed_date = day
        self.total_completed += 1
        if self.streak_count > self.best_streak:
            self.best_streak = self.streak_count
        self.save()


class ChallengeAnswer(models.Model):
    """Records each user's answer to each question (for results + completion)."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='challenge_answers',
    )
    daily_content = models.ForeignKey(
        DailyContent, on_delete=models.CASCADE, related_name='answers',
    )
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_choice = models.ForeignKey(
        Choice, on_delete=models.SET_NULL, null=True, blank=True,
    )
    is_correct = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'question')
        ordering = ['question_id']
        verbose_name = _('Challenge answer')
        verbose_name_plural = _('Challenge answers')

    def __str__(self):
        mark = 'OK' if self.is_correct else 'X'
        return f'{self.user_id} · Q{self.question_id} · {mark}'
