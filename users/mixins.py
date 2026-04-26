from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from .models import ActivityLog


class RoleRequiredMixin(LoginRequiredMixin):
    """Restrict view to one or more roles. Superusers and admins always pass."""
    required_roles = []

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        u = request.user
        if u.is_superuser or u.is_admin:
            return super().dispatch(request, *args, **kwargs)
        if self.required_roles and not any(u.has_role(r) for r in self.required_roles):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


def get_client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def log_action(user, action, details=None, request=None):
    ip = get_client_ip(request) if request else None
    ActivityLog.objects.create(
        user=user, action=action,
        details=details or {},
        ip_address=ip
    )
