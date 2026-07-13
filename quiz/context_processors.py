from datetime import date

from .models import UserStreak, DailyQuizAttempt


def quiz_streak(request):
    """Expose the user's streak + today's quiz status to every template."""
    if not request.user.is_authenticated:
        return {'quiz_streak': 0, 'quiz_best_streak': 0,
                'quiz_done_today': False, 'quiz_progress_today': 0}

    today = date.today()
    try:
        streak = request.user.quiz_streak
    except UserStreak.DoesNotExist:
        streak = None

    done_today = (streak.last_completed_day == today) if streak else False
    progress_today = DailyQuizAttempt.objects.filter(
        user=request.user, day=today
    ).count()

    return {
        'quiz_streak': streak.effective_streak if streak else 0,
        'quiz_best_streak': streak.best_streak if streak else 0,
        'quiz_done_today': done_today,
        'quiz_progress_today': progress_today,
    }
