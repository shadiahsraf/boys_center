from django import forms
from django.db.models import Count, Sum, Q, F
from django.shortcuts import render
from django.urls import reverse_lazy
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView

from users.mixins import RoleRequiredMixin
from users.models import User, Role
from .models import Team, Match, CoachAssignment, TrainingSchedule, GoalRecord, SportType


class TeamForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ['name', 'sport', 'age_group', 'logo', 'coach', 'members']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'tw-input'}),
            'sport': forms.Select(attrs={'class': 'tw-input'}),
            'age_group': forms.TextInput(attrs={'class': 'tw-input'}),
            'coach': forms.Select(attrs={'class': 'tw-input'}),
            'members': forms.SelectMultiple(attrs={'class': 'tw-input', 'size': 8}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['members'].queryset = User.objects.with_role('youth')
        self.fields['coach'].queryset = User.objects.with_role('coach')
        self.fields['coach'].required = False


class MatchForm(forms.ModelForm):
    class Meta:
        model = Match
        fields = ['sport', 'home_team', 'away_team', 'scheduled_at', 'location',
                  'home_score', 'away_score', 'is_completed', 'notes']
        widgets = {
            'sport': forms.Select(attrs={'class': 'tw-input'}),
            'home_team': forms.Select(attrs={'class': 'tw-input'}),
            'away_team': forms.Select(attrs={'class': 'tw-input'}),
            'scheduled_at': forms.DateTimeInput(attrs={'class': 'tw-input', 'type': 'datetime-local'}),
            'location': forms.TextInput(attrs={'class': 'tw-input'}),
            'home_score': forms.NumberInput(attrs={'class': 'tw-input'}),
            'away_score': forms.NumberInput(attrs={'class': 'tw-input'}),
            'notes': forms.Textarea(attrs={'class': 'tw-input', 'rows': 2}),
            'is_completed': forms.CheckboxInput(attrs={'class': 'tw-checkbox'}),
        }


class TeamListView(ListView):
    model = Team
    template_name = 'sports/team_list.html'
    context_object_name = 'teams'

    def get_queryset(self):
        qs = Team.objects.select_related('coach').annotate(member_count=Count('members'))
        sport = self.request.GET.get('sport')
        if sport:
            qs = qs.filter(sport=sport)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['sport_choices'] = SportType.choices
        ctx['filter_sport'] = self.request.GET.get('sport', '')
        return ctx


class TeamDetailView(DetailView):
    model = Team
    template_name = 'sports/team_detail.html'

    def get_queryset(self):
        return super().get_queryset().select_related('coach').prefetch_related('members')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        team = self.object
        ctx['recent_matches'] = (Match.objects
                                 .filter(Q(home_team=team) | Q(away_team=team))
                                 .order_by('-scheduled_at')[:10])
        ctx['wins'] = Match.objects.filter(
            Q(home_team=team, home_score__gt=F('away_score'), is_completed=True) |
            Q(away_team=team, away_score__gt=F('home_score'), is_completed=True)
        ).count()
        ctx['losses'] = Match.objects.filter(
            Q(home_team=team, home_score__lt=F('away_score'), is_completed=True) |
            Q(away_team=team, away_score__lt=F('home_score'), is_completed=True)
        ).count()
        ctx['draws'] = Match.objects.filter(
            Q(home_team=team) | Q(away_team=team),
            home_score=F('away_score'), is_completed=True
        ).count()
        return ctx


class TeamCreateView(RoleRequiredMixin, CreateView):
    required_roles = [Role.ADMIN, Role.COACH_MANAGER]
    model = Team
    form_class = TeamForm
    template_name = 'sports/team_form.html'
    success_url = reverse_lazy('sports:team_list')

    def form_valid(self, form):
        messages.success(self.request, _('Team created successfully.'))
        return super().form_valid(form)


class TeamUpdateView(RoleRequiredMixin, UpdateView):
    required_roles = [Role.ADMIN, Role.COACH_MANAGER]
    model = Team
    form_class = TeamForm
    template_name = 'sports/team_form.html'

    def get_success_url(self):
        return reverse_lazy('sports:team_detail', args=[self.object.pk])


class MatchListView(ListView):
    model = Match
    template_name = 'sports/match_list.html'
    context_object_name = 'matches'
    paginate_by = 20

    def get_queryset(self):
        qs = Match.objects.select_related('home_team', 'away_team').order_by('-scheduled_at')
        sport = self.request.GET.get('sport')
        status = self.request.GET.get('status')
        if sport:
            qs = qs.filter(sport=sport)
        if status == 'completed':
            qs = qs.filter(is_completed=True)
        elif status == 'upcoming':
            qs = qs.filter(is_completed=False)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['sport_choices'] = SportType.choices
        ctx['filter_sport'] = self.request.GET.get('sport', '')
        ctx['filter_status'] = self.request.GET.get('status', '')
        return ctx


class MatchCreateView(RoleRequiredMixin, CreateView):
    required_roles = [Role.ADMIN, Role.COACH_MANAGER, Role.COACH]
    model = Match
    form_class = MatchForm
    template_name = 'sports/match_form.html'
    success_url = reverse_lazy('sports:match_list')

    def form_valid(self, form):
        messages.success(self.request, _('Match scheduled.'))
        return super().form_valid(form)


class MatchUpdateView(RoleRequiredMixin, UpdateView):
    required_roles = [Role.ADMIN, Role.COACH_MANAGER, Role.COACH]
    model = Match
    form_class = MatchForm
    template_name = 'sports/match_form.html'
    success_url = reverse_lazy('sports:match_list')


class LeaderboardView(TemplateView):
    """
    Comprehensive leaderboard. Computes rankings safely with proper aggregation
    and never crashes on empty data.
    """
    template_name = 'sports/leaderboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        sport_filter = self.request.GET.get('sport', '')

        # ─── Teams Ranking ────────────────────────────────────────────
        teams_qs = Team.objects.all()
        if sport_filter:
            teams_qs = teams_qs.filter(sport=sport_filter)

        teams_data = []
        for team in teams_qs:
            home_completed = Match.objects.filter(home_team=team, is_completed=True)
            away_completed = Match.objects.filter(away_team=team, is_completed=True)

            wins = (home_completed.filter(home_score__gt=F('away_score')).count() +
                    away_completed.filter(away_score__gt=F('home_score')).count())
            losses = (home_completed.filter(home_score__lt=F('away_score')).count() +
                      away_completed.filter(away_score__lt=F('home_score')).count())
            draws = (home_completed.filter(home_score=F('away_score')).count() +
                     away_completed.filter(away_score=F('home_score')).count())

            played = wins + losses + draws
            points = wins * 3 + draws  # standard football points

            # Goals scored / conceded
            goals_for_home = home_completed.aggregate(s=Sum('home_score'))['s'] or 0
            goals_for_away = away_completed.aggregate(s=Sum('away_score'))['s'] or 0
            goals_against_home = home_completed.aggregate(s=Sum('away_score'))['s'] or 0
            goals_against_away = away_completed.aggregate(s=Sum('home_score'))['s'] or 0

            gf = goals_for_home + goals_for_away
            ga = goals_against_home + goals_against_away

            teams_data.append({
                'team': team,
                'played': played,
                'wins': wins,
                'draws': draws,
                'losses': losses,
                'gf': gf,
                'ga': ga,
                'gd': gf - ga,
                'points': points,
            })

        # Sort safely: points desc, then GD desc, then GF desc
        teams_data.sort(key=lambda t: (-t['points'], -t['gd'], -t['gf'], t['team'].name))

        ctx['teams_ranking'] = teams_data

        # ─── Top Scorers ─────────────────────────────────────────────
        scorers_qs = (GoalRecord.objects.values(
            'player__id', 'player__first_name', 'player__last_name',
            'player__member_code', 'player__photo'
        ).annotate(total=Sum('points'), goals=Count('id'))
         .order_by('-total', '-goals'))
        if sport_filter:
            scorers_qs = scorers_qs.filter(match__sport=sport_filter)
        ctx['top_scorers'] = list(scorers_qs[:15])

        ctx['sport_choices'] = SportType.choices
        ctx['filter_sport'] = sport_filter
        return ctx
