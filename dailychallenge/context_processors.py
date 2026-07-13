from datetime import date

from .models import DailyContent, ChallengeProgress


def daily_challenge(request):
    """Expose challenge streak + today's availability to all templates."""
    if not request.user.is_authenticated:
        return {'dc_streak': 0, 'dc_has_today': False, 'dc_done_today': False}

    today = date.today()
    has_today = DailyContent.objects.filter(date=today, is_published=True).exists()
    try:
        progress = request.user.challenge_progress
        streak = progress.effective_streak
        done_today = (progress.last_completed_date == today)
    except ChallengeProgress.DoesNotExist:
        streak = 0
        done_today = False

    return {
        'dc_streak': streak,
        'dc_has_today': has_today,
        'dc_done_today': done_today,
    }
