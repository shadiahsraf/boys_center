import json
from datetime import timedelta
from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, TemplateView

from users.mixins import RoleRequiredMixin, log_action
from users.models import User, Role
from .models import AttendanceSession, AttendanceRecord, SessionType


class SessionForm(forms.ModelForm):
    class Meta:
        model = AttendanceSession
        fields = ['title', 'session_type', 'sport', 'date', 'start_time', 'end_time', 'location']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }


class SessionListView(RoleRequiredMixin, ListView):
    required_roles = [Role.ADMIN, Role.COACH, Role.COACH_MANAGER]
    model = AttendanceSession
    template_name = 'attendance/session_list.html'
    context_object_name = 'sessions'
    paginate_by = 25

    def get_queryset(self):
        qs = (AttendanceSession.objects
              .select_related('coach')
              .annotate(record_count=Count('records'))
              .order_by('-date', '-start_time'))
        u = self.request.user
        if u.is_coach and not u.is_coach_manager:
            qs = qs.filter(coach=u)
        # Filters
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(location__icontains=q))
        session_type = self.request.GET.get('type')
        if session_type:
            qs = qs.filter(session_type=session_type)
        status = self.request.GET.get('status')
        if status == 'active':
            qs = qs.filter(is_open=True, expires_at__gte=timezone.now())
        elif status == 'closed':
            qs = qs.filter(Q(is_open=False) | Q(expires_at__lt=timezone.now()))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['session_types'] = SessionType.choices
        ctx['filter_q'] = self.request.GET.get('q', '')
        ctx['filter_type'] = self.request.GET.get('type', '')
        ctx['filter_status'] = self.request.GET.get('status', '')
        return ctx


class SessionCreateView(RoleRequiredMixin, CreateView):
    required_roles = [Role.ADMIN, Role.COACH, Role.COACH_MANAGER]
    model = AttendanceSession
    form_class = SessionForm
    template_name = 'attendance/session_form.html'

    def form_valid(self, form):
        form.instance.coach = self.request.user
        response = super().form_valid(form)
        # Regenerate QR with absolute URL
        base_url = f"{self.request.scheme}://{self.request.get_host()}"
        self.object.generate_qr(base_url=base_url)
        self.object.save(update_fields=['qr_code'])
        log_action(self.request.user, 'session_created', {'session': str(self.object.pk)}, self.request)
        messages.success(self.request, _('Session created. QR code is now available.'))
        return response

    def get_success_url(self):
        return reverse_lazy('attendance:detail', args=[self.object.pk])


class SessionDetailView(RoleRequiredMixin, DetailView):
    required_roles = [Role.ADMIN, Role.COACH, Role.COACH_MANAGER]
    model = AttendanceSession
    template_name = 'attendance/session_detail.html'

    def get_queryset(self):
        return (super().get_queryset()
                .select_related('coach')
                .prefetch_related('records__user'))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['records'] = self.object.records.select_related('user').order_by('-check_in_time')
        return ctx


class SessionToggleView(RoleRequiredMixin, View):
    required_roles = [Role.ADMIN, Role.COACH, Role.COACH_MANAGER]

    def post(self, request, pk):
        s = get_object_or_404(AttendanceSession, pk=pk)
        s.is_open = not s.is_open
        s.save(update_fields=['is_open'])
        log_action(request.user, 'session_toggled',
                   {'session': str(pk), 'is_open': s.is_open}, request)
        messages.success(request, _('Session status updated.'))
        return redirect('attendance:detail', pk=pk)


# ── PUBLIC CHECK-IN FLOW ────────────────────────────────────────────────────

SESSION_CHECKINS_KEY = 'attendance_checkins'


def _device_already_checked_in(request, session):
    """True if this browser session already checked someone into this attendance session.

    Prevents one phone from being passed around and checking in multiple people
    (i.e. covering for absent friends).
    """
    checkins = request.session.get(SESSION_CHECKINS_KEY, {}) or {}
    return str(session.pk) in checkins


def _record_device_checkin(request, session, user):
    """Remember on this browser session that we already did a check-in here."""
    checkins = request.session.get(SESSION_CHECKINS_KEY, {}) or {}
    checkins[str(session.pk)] = {
        'user_id': str(user.pk),
        'member_code': user.member_code,
        'name': user.get_full_name() or user.username,
    }
    request.session[SESSION_CHECKINS_KEY] = checkins
    request.session.modified = True


class CheckInLandingView(View):
    """
    The page players land on after scanning a QR code.
    They enter their member code to check in.
    No login required — anyone with the QR + member code can check in.

    Anti-fraud: one browser session can only check in ONE person per attendance
    session. If someone tries to scan again on the same phone, they get a
    "you already checked in" block. This stops a single phone from being
    passed around to check in absent friends.
    """
    def get(self, request, token):
        try:
            session = AttendanceSession.objects.get(token=token)
        except AttendanceSession.DoesNotExist:
            return render(request, 'attendance/check_in_invalid.html', {
                'error': _('Invalid or unknown QR code.')
            }, status=404)

        if not session.is_active:
            return render(request, 'attendance/check_in_invalid.html', {
                'error': _('This session is no longer accepting check-ins.'),
                'session': session,
            }, status=410)

        # Ensure this browser has a session key before we start tracking check-ins
        if not request.session.session_key:
            request.session.save()

        # Already checked in from this device? Show a friendly block.
        if _device_already_checked_in(request, session):
            prev = request.session[SESSION_CHECKINS_KEY].get(str(session.pk), {})
            return render(request, 'attendance/check_in_already.html', {
                'session': session,
                'previous_name': prev.get('name', ''),
                'previous_member_code': prev.get('member_code', ''),
            }, status=409)

        return render(request, 'attendance/check_in_form.html', {'session': session})

    def post(self, request, token):
        try:
            session = AttendanceSession.objects.get(token=token)
        except AttendanceSession.DoesNotExist:
            return render(request, 'attendance/check_in_invalid.html', {
                'error': _('Invalid or unknown QR code.')
            }, status=404)

        if not session.is_active:
            return render(request, 'attendance/check_in_invalid.html', {
                'error': _('This session has expired.'),
                'session': session,
            }, status=410)

        if not request.session.session_key:
            request.session.save()

        # Block re-submission from same device (also stops "reload the form" abuse)
        if _device_already_checked_in(request, session):
            prev = request.session[SESSION_CHECKINS_KEY].get(str(session.pk), {})
            return render(request, 'attendance/check_in_already.html', {
                'session': session,
                'previous_name': prev.get('name', ''),
                'previous_member_code': prev.get('member_code', ''),
            }, status=409)

        member_code = request.POST.get('member_code', '').strip().upper()
        if not member_code:
            messages.error(request, _('Please enter your member code.'))
            return render(request, 'attendance/check_in_form.html', {'session': session})

        try:
            user = User.objects.get(member_code__iexact=member_code)
        except User.DoesNotExist:
            messages.error(request, _('Member code not found. Please check and try again.'))
            return render(request, 'attendance/check_in_form.html', {
                'session': session,
                'submitted_code': member_code,
            })

        # Prevent duplicate check-in (same user already recorded)
        if AttendanceRecord.objects.filter(session=session, user=user).exists():
            _record_device_checkin(request, session, user)
            return render(request, 'attendance/check_in_success.html', {
                'session': session, 'user': user, 'duplicate': True,
            })

        # Determine status (late if more than 15 min after start)
        now = timezone.now()
        from datetime import datetime
        start_dt = timezone.make_aware(datetime.combine(session.date, session.start_time))
        # Only mark late if start has passed by more than 15 minutes; on-time and early are present
        delta = (now - start_dt).total_seconds() / 60
        status = 'late' if delta > 15 else 'present'

        AttendanceRecord.objects.create(session=session, user=user, status=status)
        log_action(user, 'self_checkin', {'session': str(session.pk)})
        _record_device_checkin(request, session, user)
        return render(request, 'attendance/check_in_success.html', {
            'session': session, 'user': user, 'status': status,
        })


# ── COACH MANUAL ENTRY (in case of issues) ──────────────────────────────────

class ManualCheckInView(RoleRequiredMixin, View):
    required_roles = [Role.ADMIN, Role.COACH, Role.COACH_MANAGER]

    def post(self, request, pk):
        session = get_object_or_404(AttendanceSession, pk=pk)
        member_code = request.POST.get('member_code', '').strip().upper()
        try:
            user = User.objects.get(member_code__iexact=member_code)
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'error': str(_('Member not found'))})

        record, created = AttendanceRecord.objects.get_or_create(
            session=session, user=user, defaults={'status': 'present'}
        )
        if not created:
            return JsonResponse({'success': False, 'error': str(_('Already checked in'))})

        log_action(request.user, 'manual_checkin',
                   {'session': str(pk), 'user': str(user.pk)}, request)
        return JsonResponse({
            'success': True,
            'user_name': user.get_full_name() or user.username,
            'member_code': user.member_code,
            'check_in_time': record.check_in_time.strftime('%H:%M'),
            'records_count': session.records.count(),
        })


class SessionRecordsAPIView(RoleRequiredMixin, View):
    """Live polling endpoint for the coach's session detail page."""
    required_roles = [Role.ADMIN, Role.COACH, Role.COACH_MANAGER]

    def get(self, request, pk):
        session = get_object_or_404(AttendanceSession, pk=pk)
        records = session.records.select_related('user').order_by('-check_in_time')
        data = [{
            'id': str(r.id),
            'user_name': r.user.get_full_name() or r.user.username,
            'member_code': r.user.member_code,
            'initials': r.user.initials,
            'status': r.status,
            'check_in_time': r.check_in_time.strftime('%H:%M'),
        } for r in records]
        return JsonResponse({'count': len(data), 'records': data})
