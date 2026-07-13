import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from users.models import User


class SportType(models.TextChoices):
    FOOTBALL = 'football', _('Football')
    BASKETBALL = 'basketball', _('Basketball')
    VOLLEYBALL = 'volleyball', _('Volleyball')
    HANDBALL = 'handball', _('Handball')
    TABLE_TENNIS = 'table_tennis', _('Table Tennis')


SPORT_ICONS = {
    'football': '⚽',
    'basketball': '🏀',
    'volleyball': '🏐',
    'handball': '🤾',
    'table_tennis': '🏓',
}


class Team(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('Name'), max_length=100)
    sport = models.CharField(_('Sport'), max_length=30, choices=SportType.choices)
    age_group = models.CharField(_('Age group'), max_length=30, blank=True,
                                 help_text=_('e.g. U-12, U-15, U-18'))
    logo = models.ImageField(upload_to='teams/', blank=True, null=True)
    members = models.ManyToManyField(User, related_name='teams', blank=True)
    coach = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='led_teams')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sport', 'name']

    def __str__(self):
        return f"{self.name}"

    @property
    def icon(self):
        return SPORT_ICONS.get(self.sport, '🏆')


class CoachAssignment(models.Model):
    coach = models.ForeignKey(User, on_delete=models.CASCADE, related_name='coaching_assignments')
    sport = models.CharField(max_length=30, choices=SportType.choices)
    players = models.ManyToManyField(User, related_name='coached_by', blank=True)
    team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        unique_together = ('coach', 'sport', 'team')

    def __str__(self):
        return f"{self.coach} → {self.get_sport_display()}"


class CompetitionType(models.TextChoices):
    LEAGUE = 'league', _('League')
    CUP = 'cup', _('Cup')
    FRIENDLY = 'friendly', _('Friendly')


class Competition(models.Model):
    """A grouping of matches — league season, knockout cup, or friendly series."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('Name'), max_length=120)
    competition_type = models.CharField(_('Type'), max_length=20,
                                        choices=CompetitionType.choices,
                                        default=CompetitionType.LEAGUE)
    sport = models.CharField(_('Sport'), max_length=30, choices=SportType.choices)
    season = models.CharField(_('Season'), max_length=30, blank=True,
                              help_text=_('e.g. 2025-2026'))
    is_active = models.BooleanField(_('Active'), default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_active', '-created_at']
        verbose_name = _('Competition')
        verbose_name_plural = _('Competitions')

    def __str__(self):
        suffix = f' · {self.season}' if self.season else ''
        return f'{self.name}{suffix}'

    @property
    def icon(self):
        if self.competition_type == CompetitionType.CUP:
            return '🏆'
        if self.competition_type == CompetitionType.FRIENDLY:
            return '🤝'
        return '🏅'


class Match(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sport = models.CharField(max_length=30, choices=SportType.choices)
    competition = models.ForeignKey(
        Competition, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='matches', verbose_name=_('Competition'),
    )
    home_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='home_matches')
    away_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='away_matches')
    scheduled_at = models.DateTimeField()
    location = models.CharField(max_length=200)
    home_score = models.PositiveIntegerField(null=True, blank=True)
    away_score = models.PositiveIntegerField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-scheduled_at']

    def __str__(self):
        return f"{self.home_team} vs {self.away_team} — {self.scheduled_at:%Y-%m-%d}"

    @property
    def result(self):
        if self.is_completed and self.home_score is not None:
            return f"{self.home_score} - {self.away_score}"
        return "—"

    @property
    def winner(self):
        if not self.is_completed or self.home_score is None:
            return None
        if self.home_score > self.away_score:
            return self.home_team
        if self.away_score > self.home_score:
            return self.away_team
        return None  # draw

    @property
    def icon(self):
        return SPORT_ICONS.get(self.sport, '🏆')


class GoalRecord(models.Model):
    """Generic 'score event' — works for football goals, basketball points, etc."""
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='goals')
    player = models.ForeignKey(User, on_delete=models.CASCADE, related_name='goal_records')
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    minute = models.PositiveIntegerField(null=True, blank=True)
    points = models.PositiveIntegerField(default=1, help_text=_('Goals=1, Basketball=2 or 3, etc.'))
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.player} scored in {self.match}"


class TrainingSchedule(models.Model):
    DAYS = [
        (0, _('Monday')), (1, _('Tuesday')), (2, _('Wednesday')),
        (3, _('Thursday')), (4, _('Friday')), (5, _('Saturday')), (6, _('Sunday')),
    ]
    sport = models.CharField(max_length=30, choices=SportType.choices)
    team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True)
    coach = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    day_of_week = models.IntegerField(choices=DAYS)
    start_time = models.TimeField()
    end_time = models.TimeField()
    location = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['day_of_week', 'start_time']

    def __str__(self):
        return f"{self.get_sport_display()} — {self.get_day_of_week_display()} {self.start_time}"
