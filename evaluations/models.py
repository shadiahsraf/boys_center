import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from users.models import User


class Evaluation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    coach = models.ForeignKey(User, on_delete=models.CASCADE, related_name='given_evaluations')
    player = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_evaluations')
    sport = models.CharField(_('Sport'), max_length=30, blank=True)
    performance = models.PositiveSmallIntegerField(
        _('Performance'),
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    behavior = models.PositiveSmallIntegerField(
        _('Behavior'),
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    commitment = models.PositiveSmallIntegerField(
        _('Commitment'),
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    notes = models.TextField(_('Notes'), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Evaluation')

    def __str__(self):
        return f"{self.coach} → {self.player} ({self.created_at:%Y-%m-%d})"

    @property
    def average(self):
        return round((self.performance + self.behavior + self.commitment) / 3, 1)
