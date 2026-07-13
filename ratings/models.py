"""
Ratings — anonymous, public-facing facility/activity feedback.

Admin defines facilities (swimming pool, football, basketball, etc.) and a
set of 1–5 star questions for each. They mark one or more facilities as
"open for rating", and the public can visit /rate/ to submit feedback
without logging in.

Spam prevention is best-effort: we record session_key + IP per submission
and refuse re-submission of the same (facility, session) or (facility, IP)
within a cooldown window.
"""
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Facility(models.Model):
    """A rate-able facility or activity (swimming pool, football, etc.)."""
    name = models.CharField(_('Name'), max_length=120)
    description = models.TextField(_('Description'), blank=True)
    icon = models.CharField(
        _('Icon (emoji)'), max_length=8, default='⭐',
        help_text=_('Single emoji shown on the rating page.'),
    )
    is_active = models.BooleanField(
        _('Open for rating'), default=False,
        help_text=_('When on, this facility appears on the public rating page.'),
    )
    order = models.PositiveIntegerField(_('Order'), default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Facility')
        verbose_name_plural = _('Facilities')
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    @property
    def submission_count(self):
        return self.submissions.count()

    @property
    def average_overall(self):
        agg = Answer.objects.filter(submission__facility=self).aggregate(
            avg=models.Avg('stars'),
        )
        return round(agg['avg'], 2) if agg['avg'] else None


class RatingQuestion(models.Model):
    """A single 1–5 star question for a facility."""
    facility = models.ForeignKey(
        Facility, on_delete=models.CASCADE, related_name='questions',
    )
    text = models.CharField(_('Question'), max_length=255)
    order = models.PositiveIntegerField(_('Order'), default=0)

    class Meta:
        verbose_name = _('Rating Question')
        verbose_name_plural = _('Rating Questions')
        ordering = ['order', 'id']

    def __str__(self):
        return self.text

    @property
    def average(self):
        agg = self.answers.aggregate(avg=models.Avg('stars'))
        return round(agg['avg'], 2) if agg['avg'] else None


class Submission(models.Model):
    """One anonymous rating session. Holds optional contact + spam metadata."""
    facility = models.ForeignKey(
        Facility, on_delete=models.CASCADE, related_name='submissions',
    )
    visitor_name = models.CharField(_('Name (optional)'), max_length=120, blank=True)
    phone = models.CharField(_('Phone (optional)'), max_length=30, blank=True)
    comment = models.TextField(_('Comment (optional)'), blank=True)
    session_key = models.CharField(max_length=64, blank=True, db_index=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True, db_index=True)
    user_agent = models.CharField(max_length=255, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _('Submission')
        verbose_name_plural = _('Submissions')
        ordering = ['-submitted_at']

    def __str__(self):
        return f'{self.facility.name} @ {self.submitted_at:%Y-%m-%d %H:%M}'

    @property
    def average_stars(self):
        agg = self.answers.aggregate(avg=models.Avg('stars'))
        return round(agg['avg'], 2) if agg['avg'] else None


class Answer(models.Model):
    """One star rating tied to one question inside a submission."""
    submission = models.ForeignKey(
        Submission, on_delete=models.CASCADE, related_name='answers',
    )
    question = models.ForeignKey(
        RatingQuestion, on_delete=models.CASCADE, related_name='answers',
    )
    stars = models.PositiveSmallIntegerField(_('Stars'))

    class Meta:
        verbose_name = _('Answer')
        verbose_name_plural = _('Answers')
        unique_together = [('submission', 'question')]

    def __str__(self):
        return f'{self.stars}★ — {self.question.text[:30]}'
