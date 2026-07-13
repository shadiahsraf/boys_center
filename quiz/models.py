from datetime import date, timedelta

from django.conf import settings
from django.db import models


CHOICE_LETTERS = (
    ('a', 'A'),
    ('b', 'B'),
    ('c', 'C'),
    ('d', 'D'),
)


class BibleQuestion(models.Model):
    """A single Arabic Bible MCQ used by the daily quiz."""
    text = models.TextField('سؤال')
    option_a = models.CharField('الخيار أ', max_length=200)
    option_b = models.CharField('الخيار ب', max_length=200)
    option_c = models.CharField('الخيار ج', max_length=200)
    option_d = models.CharField('الخيار د', max_length=200)
    correct = models.CharField('الإجابة الصحيحة', max_length=1, choices=CHOICE_LETTERS)
    reference = models.CharField('المرجع', max_length=120, blank=True,
                                 help_text='مثال: سفر يونان 1:17')
    is_active = models.BooleanField('فعّال', default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'سؤال إنجيلي'
        verbose_name_plural = 'الأسئلة الإنجيلية'

    def __str__(self):
        return self.text[:60]

    @property
    def correct_text(self):
        return getattr(self, f'option_{self.correct}', '')

    def options_list(self):
        """Returns list of (letter, text) — preserves a/b/c/d order."""
        return [
            ('a', self.option_a),
            ('b', self.option_b),
            ('c', self.option_c),
            ('d', self.option_d),
        ]


class DailyQuizAttempt(models.Model):
    """One row per (user, question) per day they answered."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='quiz_attempts')
    question = models.ForeignKey(BibleQuestion, on_delete=models.CASCADE,
                                 related_name='attempts')
    day = models.DateField(default=date.today)
    answer = models.CharField(max_length=1, choices=CHOICE_LETTERS)
    is_correct = models.BooleanField(default=False)
    answered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'question', 'day')
        ordering = ['-day', '-answered_at']
        indexes = [
            models.Index(fields=['user', '-day']),
        ]

    def __str__(self):
        return f'{self.user_id} · {self.day} · Q{self.question_id}'


class UserStreak(models.Model):
    """One per user — tracks current daily-quiz streak + best ever."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name='quiz_streak')
    current_streak = models.PositiveIntegerField(default=0)
    best_streak = models.PositiveIntegerField(default=0)
    total_days_completed = models.PositiveIntegerField(default=0)
    last_completed_day = models.DateField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user_id}: {self.current_streak} (best {self.best_streak})'

    @property
    def effective_streak(self) -> int:
        """Returns 0 if user skipped a day since last completion."""
        if not self.last_completed_day:
            return 0
        today = date.today()
        delta = (today - self.last_completed_day).days
        if delta <= 1:
            # Same day or yesterday — streak is still alive
            return self.current_streak
        return 0  # Broken

    def record_completion(self, day: date | None = None):
        """Called when a user finishes all 3 questions for a given day."""
        day = day or date.today()
        if self.last_completed_day == day:
            return  # Already counted today
        if self.last_completed_day == day - timedelta(days=1):
            self.current_streak += 1
        else:
            # First time, or streak was broken
            self.current_streak = 1
        self.last_completed_day = day
        self.total_days_completed += 1
        if self.current_streak > self.best_streak:
            self.best_streak = self.current_streak
        self.save()
