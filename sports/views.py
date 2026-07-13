from django import forms
from django.db.models import Count, Sum, Q, F
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView

from users.mixins import RoleRequiredMixin
from users.models import User, Role
from .models import (Team, Match, CoachAssignment, TrainingSchedule,
                     GoalRecord, SportType, Competition, CompetitionType)


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
        fields = ['sport', 'competition', 'home_team', 'away_team', 'scheduled_at',
                  'location', 'home_score', 'away_score', 'is_completed', 'notes']
        widgets = {
            'sport': forms.Select(attrs={'class': 'tw-input'}),
            'competition': forms.Select(attrs={'class': 'tw-input'}),
            'home_team': forms.Select(attrs={'class': 'tw-input'}),
            'away_team': forms.Select(attrs={'class': 'tw-input'}),
            'scheduled_at': forms.DateTimeInput(attrs={'class': 'tw-input', 'type': 'datetime-local'}),
            'location': forms.TextInput(attrs={'class': 'tw-input'}),
            'home_score': forms.NumberInput(attrs={'class': 'tw-input'}),
            'away_score': forms.NumberInput(attrs={'class': 'tw-input'}),
            'notes': forms.Textarea(attrs={'class': 'tw-input', 'rows': 2}),
            'is_completed': forms.CheckboxInput(attrs={'class': 'tw-checkbox'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['competition'].required = False
        self.fields['competition'].queryset = Competition.objects.filter(is_active=True)
        self.fields['competition'].empty_label = _('— No competition —')


class CompetitionForm(forms.ModelForm):
    class Meta:
        model = Competition
        fields = ['name', 'competition_type', 'sport', 'season', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'tw-input'}),
            'competition_type': forms.Select(attrs={'class': 'tw-input'}),
            'sport': forms.Select(attrs={'class': 'tw-input'}),
            'season': forms.TextInput(attrs={'class': 'tw-input', 'placeholder': '2025-2026'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'tw-checkbox'}),
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
    and never crashes on empty data. Filterable by sport AND competition.
    """
    template_name = 'sports/leaderboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        sport_filter = self.request.GET.get('sport', '')
        comp_filter = self.request.GET.get('competition', '')

        match_filter = Q(is_completed=True)
        if sport_filter:
            match_filter &= Q(sport=sport_filter)
        if comp_filter:
            match_filter &= Q(competition_id=comp_filter)

        # ─── Teams Ranking ────────────────────────────────────────────
        teams_qs = Team.objects.all()
        if sport_filter:
            teams_qs = teams_qs.filter(sport=sport_filter)

        teams_data = []
        for team in teams_qs:
            home_completed = Match.objects.filter(match_filter, home_team=team)
            away_completed = Match.objects.filter(match_filter, away_team=team)

            wins = (home_completed.filter(home_score__gt=F('away_score')).count() +
                    away_completed.filter(away_score__gt=F('home_score')).count())
            losses = (home_completed.filter(home_score__lt=F('away_score')).count() +
                      away_completed.filter(away_score__lt=F('home_score')).count())
            draws = (home_completed.filter(home_score=F('away_score')).count() +
                     away_completed.filter(away_score=F('home_score')).count())

            played = wins + losses + draws
            points = wins * 3 + draws  # standard football points

            goals_for_home = home_completed.aggregate(s=Sum('home_score'))['s'] or 0
            goals_for_away = away_completed.aggregate(s=Sum('away_score'))['s'] or 0
            goals_against_home = home_completed.aggregate(s=Sum('away_score'))['s'] or 0
            goals_against_away = away_completed.aggregate(s=Sum('home_score'))['s'] or 0

            gf = goals_for_home + goals_for_away
            ga = goals_against_home + goals_against_away

            # Don't include teams with no matches when filtering — keeps the table clean
            if (sport_filter or comp_filter) and played == 0:
                continue

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
        scorers_qs = GoalRecord.objects.all()
        if sport_filter:
            scorers_qs = scorers_qs.filter(match__sport=sport_filter)
        if comp_filter:
            scorers_qs = scorers_qs.filter(match__competition_id=comp_filter)
        scorers = (scorers_qs.values(
            'player__id', 'player__first_name', 'player__last_name',
            'player__member_code', 'player__photo'
        ).annotate(total=Sum('points'), goals=Count('id'))
         .order_by('-total', '-goals'))
        ctx['top_scorers'] = list(scorers[:15])

        # ─── Competition list for filter pills ───────────────────────
        comps_qs = Competition.objects.filter(is_active=True)
        if sport_filter:
            comps_qs = comps_qs.filter(sport=sport_filter)
        ctx['competitions'] = comps_qs
        ctx['active_competition'] = (Competition.objects.filter(pk=comp_filter).first()
                                      if comp_filter else None)

        ctx['sport_choices'] = SportType.choices
        ctx['filter_sport'] = sport_filter
        ctx['filter_competition'] = comp_filter
        return ctx


# ═══════════════════════════════════════════════════════════════════════════
# Competition CRUD
# ═══════════════════════════════════════════════════════════════════════════

class CompetitionListView(ListView):
    model = Competition
    template_name = 'sports/competition_list.html'
    context_object_name = 'competitions'
    paginate_by = 30

    def get_queryset(self):
        qs = Competition.objects.annotate(matches_count=Count('matches'))
        sport = self.request.GET.get('sport')
        if sport:
            qs = qs.filter(sport=sport)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['sport_choices'] = SportType.choices
        ctx['filter_sport'] = self.request.GET.get('sport', '')
        return ctx


class CompetitionCreateView(RoleRequiredMixin, CreateView):
    required_roles = [Role.ADMIN, Role.COACH_MANAGER]
    model = Competition
    form_class = CompetitionForm
    template_name = 'sports/competition_form.html'
    success_url = reverse_lazy('sports:competition_list')

    def form_valid(self, form):
        messages.success(self.request, _('Competition created.'))
        return super().form_valid(form)


class CompetitionUpdateView(RoleRequiredMixin, UpdateView):
    required_roles = [Role.ADMIN, Role.COACH_MANAGER]
    model = Competition
    form_class = CompetitionForm
    template_name = 'sports/competition_form.html'
    success_url = reverse_lazy('sports:competition_list')

    def form_valid(self, form):
        messages.success(self.request, _('Competition updated.'))
        return super().form_valid(form)


# ═══════════════════════════════════════════════════════════════════════════
# Finish-match view — coach/manager enters final score + goal scorers
# ═══════════════════════════════════════════════════════════════════════════

class MatchFinishView(RoleRequiredMixin, View):
    """
    Post-match flow: pick winner via scores, record goal scorers.
    GET: render form with all eligible players from both teams.
    POST: persist scores + bulk-create GoalRecord entries.
    """
    required_roles = [Role.ADMIN, Role.COACH_MANAGER, Role.COACH]
    template_name = 'sports/match_finish.html'

    def _get_match(self, pk):
        return get_object_or_404(
            Match.objects.select_related('home_team', 'away_team', 'competition'),
            pk=pk,
        )

    def get(self, request, pk):
        match = self._get_match(pk)
        ctx = {
            'match': match,
            'home_players': list(match.home_team.members.all().order_by('first_name')),
            'away_players': list(match.away_team.members.all().order_by('first_name')),
            'existing_goals': list(
                match.goals.select_related('player', 'team').order_by('minute', 'id')
            ),
        }
        return render(request, self.template_name, ctx)

    def post(self, request, pk):
        match = self._get_match(pk)

        try:
            home_score = int(request.POST.get('home_score') or 0)
            away_score = int(request.POST.get('away_score') or 0)
        except ValueError:
            messages.error(request, _('Scores must be whole numbers.'))
            return redirect('sports:match_finish', pk=pk)

        if home_score < 0 or away_score < 0:
            messages.error(request, _('Scores cannot be negative.'))
            return redirect('sports:match_finish', pk=pk)

        # Save match
        match.home_score = home_score
        match.away_score = away_score
        match.is_completed = True
        notes = (request.POST.get('notes') or '').strip()
        if notes:
            match.notes = notes
        match.save()

        # Replace any existing goal records with the freshly-submitted set.
        match.goals.all().delete()

        scorer_player_ids = request.POST.getlist('scorer_player[]')
        scorer_team_sides = request.POST.getlist('scorer_team[]')
        scorer_minutes = request.POST.getlist('scorer_minute[]')
        scorer_points = request.POST.getlist('scorer_points[]')

        records = []
        for i, player_id in enumerate(scorer_player_ids):
            if not player_id:
                continue
            try:
                player = User.objects.get(pk=player_id)
            except (User.DoesNotExist, ValueError):
                continue
            side = scorer_team_sides[i] if i < len(scorer_team_sides) else 'home'
            team = match.home_team if side == 'home' else match.away_team
            minute = None
            if i < len(scorer_minutes) and scorer_minutes[i].strip():
                try:
                    minute = max(0, int(scorer_minutes[i]))
                except ValueError:
                    minute = None
            try:
                points = int(scorer_points[i]) if i < len(scorer_points) and scorer_points[i] else 1
            except ValueError:
                points = 1
            points = max(1, points)
            records.append(GoalRecord(
                match=match, player=player, team=team,
                minute=minute, points=points,
            ))

        if records:
            GoalRecord.objects.bulk_create(records)

        winner = match.winner
        if winner is None and match.is_completed:
            messages.success(request, _('Match finished — draw recorded.'))
        elif winner:
            messages.success(request,
                             _('Match finished — winner: %(team)s.') % {'team': winner.name})
        return redirect('sports:match_list')
