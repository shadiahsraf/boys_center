import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from users.models import User


class EventType(models.TextChoices):
    TRAINING = 'training', _('Training')
    MATCH = 'match', _('Match')
    PRAYER = 'prayer', _('Prayer Meeting')
    PARENT = 'parent', _('Parent Activity')
    CAMP = 'camp', _('Camp')
    OTHER = 'other', _('Other Event')


EVENT_COLORS = {
    'training': 'green',
    'match': 'red',
    'prayer': 'amber',
    'parent': 'sky',
    'camp': 'purple',
    'other': 'slate',
}


class Event(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(_('Title'), max_length=300)
    event_type = models.CharField(_('Event type'), max_length=20, choices=EventType.choices)
    description = models.TextField(_('Description'), blank=True)
    start_datetime = models.DateTimeField(_('Start'))
    end_datetime = models.DateTimeField(_('End'), null=True, blank=True)
    location = models.CharField(_('Location'), max_length=300)
    assigned_groups = models.JSONField(default=list, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['start_datetime']

    def __str__(self):
        return f"{self.title} — {self.start_datetime:%Y-%m-%d}"

    @property
    def color(self):
        return EVENT_COLORS.get(self.event_type, 'slate')


class ParentActivity(models.Model):
    event = models.OneToOneField(Event, on_delete=models.CASCADE, related_name='parent_activity')
    participants = models.ManyToManyField(User, blank=True, related_name='parent_activities')
    max_participants = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return f"Parent Activity: {self.event.title}"
