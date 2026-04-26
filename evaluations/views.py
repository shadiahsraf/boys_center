from django import forms
from django.contrib import messages
from django.db.models import Avg, Q
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, ListView, DetailView

from users.mixins import RoleRequiredMixin, log_action
from users.models import User, Role
from .models import Evaluation


class EvaluationForm(forms.ModelForm):
    class Meta:
        model = Evaluation
        fields = ['player', 'sport', 'performance', 'behavior', 'commitment', 'notes']
        widgets = {
            'player': forms.Select(attrs={'class': 'tw-input'}),
            'sport': forms.Select(attrs={'class': 'tw-input'}),
            'performance': forms.HiddenInput(),
            'behavior': forms.HiddenInput(),
            'commitment': forms.HiddenInput(),
            'notes': forms.Textarea(attrs={'class': 'tw-input', 'rows': 3,
                                           'placeholder': _('Optional notes about the player...')}),
        }

    def __init__(self, coach=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from sports.models import SportType
        self.fields['sport'].choices = [('', '—')] + list(SportType.choices)
        self.fields['sport'].required = False
        if coach and not coach.is_admin:
            from sports.models import CoachAssignment
            player_ids = list(CoachAssignment.objects
                              .filter(coach=coach)
                              .values_list('players__id', flat=True))
            qs = User.objects.with_role('youth')
            if player_ids:
                qs = qs.filter(id__in=player_ids)
            self.fields['player'].queryset = qs
        else:
            self.fields['player'].queryset = User.objects.with_role('youth')


class EvaluationListView(RoleRequiredMixin, ListView):
    required_roles = [Role.COACH, Role.ADMIN, Role.COACH_MANAGER]
    model = Evaluation
    template_name = 'evaluations/evaluation_list.html'
    context_object_name = 'evaluations'
    paginate_by = 25

    def get_queryset(self):
        qs = Evaluation.objects.select_related('coach', 'player')
        u = self.request.user
        if u.is_coach and not u.is_coach_manager:
            qs = qs.filter(coach=u)
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(player__first_name__icontains=q) |
                Q(player__last_name__icontains=q) |
                Q(coach__first_name__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['filter_q'] = self.request.GET.get('q', '')
        return ctx


class EvaluationCreateView(RoleRequiredMixin, CreateView):
    required_roles = [Role.COACH, Role.ADMIN, Role.COACH_MANAGER]
    model = Evaluation
    form_class = EvaluationForm
    template_name = 'evaluations/evaluation_form.html'
    success_url = reverse_lazy('evaluations:list')

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw['coach'] = self.request.user
        return kw

    def form_valid(self, form):
        form.instance.coach = self.request.user
        log_action(self.request.user, 'evaluation_created',
                   {'player': str(form.instance.player_id)}, self.request)
        messages.success(self.request, _('Evaluation saved successfully.'))
        return super().form_valid(form)


class PlayerEvaluationView(RoleRequiredMixin, ListView):
    required_roles = [Role.YOUTH, Role.PARENT, Role.COACH, Role.ADMIN, Role.COACH_MANAGER]
    template_name = 'evaluations/player_evaluations.html'
    context_object_name = 'evaluations'

    def get_queryset(self):
        return (Evaluation.objects
                .filter(player_id=self.kwargs['player_id'])
                .select_related('coach')
                .order_by('-created_at'))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        player = User.objects.get(pk=self.kwargs['player_id'])
        agg = Evaluation.objects.filter(player=player).aggregate(
            p=Avg('performance'), b=Avg('behavior'), c=Avg('commitment')
        )
        ctx.update({
            'player': player,
            'avg_performance': round(agg['p'], 1) if agg['p'] else None,
            'avg_behavior': round(agg['b'], 1) if agg['b'] else None,
            'avg_commitment': round(agg['c'], 1) if agg['c'] else None,
            'eval_count': self.get_queryset().count(),
        })
        return ctx
