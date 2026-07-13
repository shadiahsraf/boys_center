from datetime import date, timedelta
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.db.models import Avg, Count, Q
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import (CreateView, DetailView, DeleteView, ListView,
                                  TemplateView, UpdateView)

from .forms import (LoginForm, ProfilePhotoForm, ProfileSelfUpdateForm,
                    UserCreateForm, UserUpdateForm)
from .mixins import RoleRequiredMixin
from .models import User, Role, ActivityLog


class LandingView(TemplateView):
    """Public landing page. Authenticated users get redirected to their dashboard."""
    template_name = 'landing.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from news.models import NewsPost
        from events.models import Event
        ctx['featured_news'] = NewsPost.objects.filter(is_published=True, is_featured=True).select_related('author')[:3]
        ctx['latest_news'] = NewsPost.objects.filter(is_published=True).select_related('author')[:6]
        ctx['upcoming_events'] = (Event.objects
                                  .filter(start_datetime__gte=timezone.now())
                                  .order_by('start_datetime')[:6])
        # Public stats
        ctx['stats'] = {
            'youth': User.objects.with_role('youth').count(),
            'coaches': User.objects.with_role('coach').count(),
            'teams': __import__('sports').models.Team.objects.count(),
        }
        return ctx


class CustomLoginView(LoginView):
    form_class = LoginForm
    template_name = 'users/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy('dashboard')


class DashboardView(LoginRequiredMixin, TemplateView):
    """Single dashboard that adapts based on role."""
    def get_template_names(self):
        u = self.request.user
        if u.is_admin:
            return ['dashboard/admin.html']
        if u.is_coach_manager:
            return ['dashboard/manager.html']
        if u.is_coach:
            return ['dashboard/coach.html']
        if u.is_parent:
            return ['dashboard/parent.html']
        return ['dashboard/youth.html']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from news.models import NewsPost
        from events.models import Event
        from attendance.models import AttendanceSession, AttendanceRecord
        from sports.models import Team, Match
        from evaluations.models import Evaluation

        u = self.request.user
        today = date.today()
        week_ago = today - timedelta(days=7)

        ctx['latest_news'] = NewsPost.objects.filter(is_published=True).select_related('author')[:5]
        ctx['upcoming_events'] = (Event.objects
                                  .filter(start_datetime__gte=timezone.now())
                                  .order_by('start_datetime')[:6])

        # Admin / Manager stats
        if u.is_admin or u.is_coach_manager:
            ctx.update({
                'total_members': User.objects.count(),
                'total_youth': User.objects.with_role('youth').count(),
                'total_coaches': User.objects.with_role('coach').count(),
                'total_parents': User.objects.with_role('parent').count(),
                'total_teams': Team.objects.count(),
                'recent_sessions': AttendanceSession.objects.filter(date__gte=week_ago).count(),
                'recent_evaluations': Evaluation.objects.filter(created_at__date__gte=week_ago).count(),
                'upcoming_matches': Match.objects.filter(scheduled_at__gte=timezone.now()).count(),
            })
            # Attendance trend (last 14 days)
            trend = []
            for i in range(13, -1, -1):
                d = today - timedelta(days=i)
                count = AttendanceRecord.objects.filter(check_in_time__date=d).count()
                trend.append({'date': d.strftime('%b %d'), 'count': count})
            ctx['attendance_trend'] = trend

        if u.is_coach:
            ctx['my_sessions'] = (AttendanceSession.objects
                                  .filter(coach=u).order_by('-date')[:5])
            ctx['my_active_sessions'] = AttendanceSession.objects.filter(
                coach=u, is_open=True, expires_at__gte=timezone.now()
            )
            ctx['my_evaluations_count'] = Evaluation.objects.filter(coach=u).count()

        if u.is_coach_manager and not u.is_admin:
            ctx['recent_logs'] = ActivityLog.objects.select_related('user')[:10]

        if u.is_parent:
            children = u.children.all()
            ctx['my_children'] = children
            child_attendance_qs = AttendanceRecord.objects.filter(user__in=children)
            child_evaluations_qs = Evaluation.objects.filter(player__in=children)
            ctx['child_attendance'] = (child_attendance_qs
                                       .select_related('session', 'user')
                                       .order_by('-check_in_time')[:8])
            ctx['child_evaluations'] = (child_evaluations_qs
                                        .select_related('player', 'coach')
                                        .order_by('-created_at')[:5])
            # Real totals so hero stats are accurate (not capped at slice size)
            ctx['child_attendance_total'] = child_attendance_qs.count()
            ctx['child_evaluations_total'] = child_evaluations_qs.count()

        if u.is_youth:
            attendance_qs = AttendanceRecord.objects.filter(user=u)
            evals_qs = Evaluation.objects.filter(player=u)
            ctx['my_attendance'] = (attendance_qs
                                    .select_related('session')
                                    .order_by('-check_in_time')[:8])
            ctx['my_evaluations'] = evals_qs.order_by('-created_at')[:5]
            agg = evals_qs.aggregate(
                p=Avg('performance'), b=Avg('behavior'), c=Avg('commitment')
            )
            ctx['eval_summary'] = {
                'performance': round(agg['p'], 1) if agg['p'] else None,
                'behavior': round(agg['b'], 1) if agg['b'] else None,
                'commitment': round(agg['c'], 1) if agg['c'] else None,
            }
            ctx['attendance_count'] = attendance_qs.count()
            ctx['evaluations_total'] = evals_qs.count()

        return ctx


class UserListView(RoleRequiredMixin, ListView):
    required_roles = [Role.ADMIN, Role.COACH_MANAGER]
    model = User
    template_name = 'users/user_list.html'
    context_object_name = 'users'
    paginate_by = 24

    def get_queryset(self):
        qs = User.objects.all()
        q = self.request.GET.get('q', '').strip()
        role = self.request.GET.get('role', '').strip()
        if q:
            qs = qs.filter(
                Q(first_name__icontains=q) |
                Q(last_name__icontains=q) |
                Q(username__icontains=q) |
                Q(member_code__icontains=q) |
                Q(phone__icontains=q)
            )
        if role:
            qs = qs.with_role(role)
        return qs.order_by('first_name', 'last_name')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['filter_q'] = self.request.GET.get('q', '')
        ctx['filter_role'] = self.request.GET.get('role', '')
        ctx['roles'] = [(r.value, r.label) for r in Role]
        return ctx


class UserCreateView(RoleRequiredMixin, CreateView):
    required_roles = [Role.ADMIN]
    model = User
    form_class = UserCreateForm
    template_name = 'users/user_form.html'
    success_url = reverse_lazy('users:list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, _('User created successfully.'))
        return super().form_valid(form)


class UserDetailView(LoginRequiredMixin, DetailView):
    model = User
    template_name = 'users/user_detail.html'
    context_object_name = 'profile_user'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from evaluations.models import Evaluation
        from attendance.models import AttendanceRecord
        u = self.object
        ctx['evaluations'] = (Evaluation.objects.filter(player=u)
                              .select_related('coach').order_by('-created_at')[:10])
        ctx['recent_attendance'] = (AttendanceRecord.objects.filter(user=u)
                                    .select_related('session').order_by('-check_in_time')[:10])
        agg = Evaluation.objects.filter(player=u).aggregate(
            p=Avg('performance'), b=Avg('behavior'), c=Avg('commitment')
        )
        ctx['avg_performance'] = round(agg['p'], 1) if agg['p'] else None
        ctx['avg_behavior'] = round(agg['b'], 1) if agg['b'] else None
        ctx['avg_commitment'] = round(agg['c'], 1) if agg['c'] else None
        return ctx


class UserUpdateView(RoleRequiredMixin, UpdateView):
    required_roles = [Role.ADMIN]
    model = User
    form_class = UserUpdateForm
    template_name = 'users/user_form.html'

    def get_success_url(self):
        return reverse_lazy('users:detail', args=[self.object.pk])


class ProfileSelfUpdateView(LoginRequiredMixin, UpdateView):
    """Any authenticated user edits their own contact info + parent contact."""
    model = User
    form_class = ProfileSelfUpdateForm
    template_name = 'users/profile_self_form.html'
    success_url = reverse_lazy('dashboard')

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _('Profile updated.'))
        return response


class ProfilePhotoUpdateView(LoginRequiredMixin, UpdateView):
    """Any authenticated user can change their OWN profile photo."""
    model = User
    form_class = ProfilePhotoForm
    template_name = 'users/profile_photo_form.html'
    success_url = reverse_lazy('dashboard')

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _('Profile photo updated.'))
        return response


class ProfilePhotoDeleteView(LoginRequiredMixin, TemplateView):
    """Removes the user's photo (so initials show again)."""
    def post(self, request, *args, **kwargs):
        u = request.user
        if u.photo:
            u.photo.delete(save=False)
            u.photo = None
            u.save(update_fields=['photo'])
            messages.success(request, _('Profile photo removed.'))
        return redirect('dashboard')

    def get(self, request, *args, **kwargs):
        return redirect('dashboard')


class ActivityLogView(RoleRequiredMixin, ListView):
    required_roles = [Role.ADMIN, Role.COACH_MANAGER]
    template_name = 'users/activity_log.html'
    context_object_name = 'logs'
    paginate_by = 50

    def get_queryset(self):
        qs = ActivityLog.objects.select_related('user').order_by('-timestamp')
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(user__first_name__icontains=q) |
                Q(user__last_name__icontains=q) |
                Q(action__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['filter_q'] = self.request.GET.get('q', '')
        return ctx


class UserDeleteView(RoleRequiredMixin, DeleteView):
    """Admin-only: delete a user (soft-protect: prevent deleting self or last admin)."""
    required_roles = [Role.ADMIN]
    model = User
    template_name = 'users/user_confirm_delete.html'
    success_url = reverse_lazy('users:list')

    def dispatch(self, request, *args, **kwargs):
        # Prevent self-deletion
        target = self.get_object() if request.user.is_authenticated else None
        if target and target.pk == request.user.pk:
            from django.contrib import messages as msgs
            msgs.error(request, _("You cannot delete your own account."))
            from django.shortcuts import redirect
            return redirect('users:detail', pk=target.pk)
        # Prevent deleting the last admin
        if target and target.is_admin:
            other_admins = User.objects.with_role('admin').exclude(pk=target.pk).count()
            if other_admins == 0:
                from django.contrib import messages as msgs
                msgs.error(request, _("Cannot delete the only remaining admin."))
                from django.shortcuts import redirect
                return redirect('users:detail', pk=target.pk)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        from django.contrib import messages as msgs
        from .mixins import log_action
        target = self.get_object()
        log_action(self.request.user, 'user_deleted',
                   {'target_id': str(target.pk),
                    'target_username': target.username}, self.request)
        msgs.success(self.request, _("Member %(name)s has been deleted.") % {'name': target.get_full_name() or target.username})
        return super().form_valid(form)
