"""
Signal handlers that create Notification records when interesting events happen
in the rest of the app.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse, NoReverseMatch
from django.utils.translation import gettext_lazy as _

from .models import Notification, NotificationKind


def _safe_url(name, *args):
    try:
        return reverse(name, args=args)
    except NoReverseMatch:
        return ''


def _bulk_notify(recipients, *, kind, title, message='', url=''):
    """Create one notification per recipient in a single bulk_create."""
    objs = [
        Notification(
            recipient=r, kind=kind, title=title,
            message=message[:400], url=url,
        )
        for r in recipients if r is not None
    ]
    if objs:
        Notification.objects.bulk_create(objs, ignore_conflicts=True)


# ── Evaluation created → notify the player + their parents ─────────────────
@receiver(post_save, sender='evaluations.Evaluation')
def on_evaluation_created(sender, instance, created, **kwargs):
    if not created:
        return
    player = instance.player
    coach_name = instance.coach.get_full_name() if instance.coach else _('A coach')
    url = _safe_url('users:detail', player.pk)

    recipients = [player]
    # Notify parents too
    recipients.extend(list(player.parents.all()))

    _bulk_notify(
        recipients,
        kind=NotificationKind.EVALUATION,
        title=str(_('New evaluation from %(coach)s') % {'coach': coach_name}),
        message=str(_('%(player)s received a new evaluation.') % {'player': player.first_name or player.username}),
        url=url,
    )


# ── New attendance session → notify open audience (youth + their parents) ──
@receiver(post_save, sender='attendance.AttendanceSession')
def on_session_created(sender, instance, created, **kwargs):
    if not created:
        return

    # Lazy import to avoid circulars
    from django.contrib.auth import get_user_model
    User = get_user_model()
    # Notify all youth and parents
    audience = list(
        User.objects.filter(is_active=True).filter(
            roles__icontains='"youth"',
        )
    ) + list(
        User.objects.filter(is_active=True).filter(
            roles__icontains='"parent"',
        )
    )

    url = _safe_url('attendance:detail', instance.pk)
    _bulk_notify(
        audience,
        kind=NotificationKind.SESSION,
        title=str(_('New session: %(title)s') % {'title': instance.title}),
        message=str(_('%(date)s at %(location)s') % {
            'date': instance.date.strftime('%b %d'),
            'location': instance.location or '',
        }),
        url=url,
    )


# ── Attendance check-in recorded → notify parents of the youth ─────────────
@receiver(post_save, sender='attendance.AttendanceRecord')
def on_attendance_recorded(sender, instance, created, **kwargs):
    if not created:
        return
    player = instance.user
    parents = list(player.parents.all())
    if not parents:
        return

    status_label = {
        'present': _('Present'),
        'late': _('Late'),
        'excused': _('Excused'),
        'absent': _('Absent'),
    }.get(instance.status, instance.status)

    _bulk_notify(
        parents,
        kind=NotificationKind.ATTENDANCE,
        title=str(_('%(player)s checked in') % {'player': player.first_name or player.username}),
        message=str(_('Status: %(status)s · %(session)s') % {
            'status': status_label,
            'session': instance.session.title if instance.session_id else '',
        }),
        url=_safe_url('users:detail', player.pk),
    )


# ── News post published → notify everyone ──────────────────────────────────
@receiver(post_save, sender='news.NewsPost')
def on_news_posted(sender, instance, created, **kwargs):
    if not instance.is_published:
        return
    # Only notify on the first publish (no easy way to detect transitions cheaply
    # without an extra field; we settle for "first save and is_published" via `created`)
    if not created:
        return

    from django.contrib.auth import get_user_model
    User = get_user_model()
    recipients = list(User.objects.filter(is_active=True).exclude(pk=getattr(instance.author, 'pk', None) or 0))

    _bulk_notify(
        recipients,
        kind=NotificationKind.NEWS,
        title=str(_('News: %(title)s') % {'title': instance.title}),
        message=(instance.excerpt or '')[:200],
        url=_safe_url('news:detail', instance.pk),
    )


# ── Match completed → notify players of both teams + their parents ─────────
@receiver(post_save, sender='sports.Match')
def on_match_completed(sender, instance, created, **kwargs):
    # Only fire when transitioning to completed (not on every save).
    # Detect via "completed and has a score and at least 1 goal record OR coach saved with completed=True".
    if not instance.is_completed:
        return
    # Guard: bail if we've already notified for this match (rough check)
    if Notification.objects.filter(
        kind=NotificationKind.SYSTEM,
        title__startswith=f'__match_done_{instance.pk}'
    ).exists():
        return

    home_team = instance.home_team
    away_team = instance.away_team
    winner = instance.winner

    # Collect recipients: players in either team + their parents (deduped)
    from django.contrib.auth import get_user_model
    User = get_user_model()
    members = list(home_team.members.all()) + list(away_team.members.all())
    parent_ids = set()
    for m in members:
        for p in m.parents.all():
            parent_ids.add(p.pk)
    recipients = {m.pk: m for m in members}
    if parent_ids:
        for p in User.objects.filter(pk__in=parent_ids):
            recipients[p.pk] = p
    recipients = list(recipients.values())

    if winner:
        title = str(_('%(winner)s won %(home)s vs %(away)s') % {
            'winner': winner.name,
            'home': home_team.name,
            'away': away_team.name,
        })
    else:
        title = str(_('Draw: %(home)s vs %(away)s') % {
            'home': home_team.name, 'away': away_team.name,
        })
    msg = str(_('Final score: %(h)s — %(a)s') % {
        'h': instance.home_score, 'a': instance.away_score,
    })

    _bulk_notify(
        recipients,
        kind=NotificationKind.SYSTEM,
        title=title,
        message=msg,
        url=_safe_url('sports:match_finish', instance.pk),
    )
    # Mark to avoid duplicate-notification storms on subsequent saves
    Notification.objects.create(
        recipient=recipients[0] if recipients else instance.home_team.coach or User.objects.first(),
        kind=NotificationKind.SYSTEM,
        title=f'__match_done_{instance.pk}',
        is_read=True,
    )


# ── New event added → notify everyone ──────────────────────────────────────
@receiver(post_save, sender='events.Event')
def on_event_created(sender, instance, created, **kwargs):
    if not created:
        return

    from django.contrib.auth import get_user_model
    User = get_user_model()
    recipients = list(User.objects.filter(is_active=True))

    _bulk_notify(
        recipients,
        kind=NotificationKind.EVENT,
        title=str(_('Upcoming: %(title)s') % {'title': instance.title}),
        message=str(_('%(date)s · %(location)s') % {
            'date': instance.start_datetime.strftime('%b %d, %H:%M') if instance.start_datetime else '',
            'location': instance.location or '',
        }),
        url=_safe_url('events:detail', instance.pk),
    )
