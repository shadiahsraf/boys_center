from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class NotificationKind(models.TextChoices):
    EVALUATION = 'evaluation', _('New evaluation')
    SESSION = 'session', _('New session')
    NEWS = 'news', _('News posted')
    EVENT = 'event', _('Upcoming event')
    ATTENDANCE = 'attendance', _('Attendance recorded')
    SYSTEM = 'system', _('System notice')


class Notification(models.Model):
    """A single in-app notification for one recipient."""
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    kind = models.CharField(
        _('Kind'),
        max_length=20,
        choices=NotificationKind.choices,
        default=NotificationKind.SYSTEM,
    )
    title = models.CharField(_('Title'), max_length=200)
    message = models.CharField(_('Message'), max_length=400, blank=True)
    url = models.CharField(_('Link'), max_length=400, blank=True)
    is_read = models.BooleanField(_('Read'), default=False)
    created_at = models.DateTimeField(_('Created'), auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read', '-created_at']),
        ]
        verbose_name = _('Notification')
        verbose_name_plural = _('Notifications')

    def __str__(self):
        return f'{self.recipient}: {self.title}'
