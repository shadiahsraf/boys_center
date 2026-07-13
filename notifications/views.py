from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST
from django.views.generic import ListView

from .models import Notification


class NotificationListView(LoginRequiredMixin, ListView):
    """Full notifications inbox for the current user."""
    template_name = 'notifications/list.html'
    context_object_name = 'notifications'
    paginate_by = 30

    def get_queryset(self):
        qs = Notification.objects.filter(recipient=self.request.user)
        kind = self.request.GET.get('kind', '').strip()
        if kind:
            qs = qs.filter(kind=kind)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['filter_kind'] = self.request.GET.get('kind', '')
        ctx['total_unread'] = Notification.objects.filter(
            recipient=self.request.user, is_read=False
        ).count()
        return ctx


@login_required
@require_POST
def mark_all_read(request):
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    messages.success(request, _('All notifications marked as read.'))
    return redirect(request.META.get('HTTP_REFERER') or reverse_lazy('notifications:list'))


@login_required
def open_notification(request, pk):
    """Mark a single notification read and redirect to its target URL (or list)."""
    n = get_object_or_404(Notification, pk=pk, recipient=request.user)
    if not n.is_read:
        n.is_read = True
        n.save(update_fields=['is_read'])
    if n.url:
        return HttpResponseRedirect(n.url)
    return redirect('notifications:list')
