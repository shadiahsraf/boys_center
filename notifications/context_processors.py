from .models import Notification


def notifications(request):
    """Inject unread notification count + latest 8 for the topbar dropdown."""
    if not request.user.is_authenticated:
        return {'unread_notifications_count': 0, 'recent_notifications': []}

    qs = Notification.objects.filter(recipient=request.user)
    unread_count = qs.filter(is_read=False).count()
    recent = list(qs[:8])
    return {
        'unread_notifications_count': unread_count,
        'recent_notifications': recent,
    }
