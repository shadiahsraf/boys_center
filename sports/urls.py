from django.urls import path
from . import views

app_name = 'sports'

urlpatterns = [
    path('teams/', views.TeamListView.as_view(), name='team_list'),
    path('teams/new/', views.TeamCreateView.as_view(), name='team_create'),
    path('teams/<uuid:pk>/', views.TeamDetailView.as_view(), name='team_detail'),
    path('teams/<uuid:pk>/edit/', views.TeamUpdateView.as_view(), name='team_update'),

    path('matches/', views.MatchListView.as_view(), name='match_list'),
    path('matches/new/', views.MatchCreateView.as_view(), name='match_create'),
    path('matches/<uuid:pk>/edit/', views.MatchUpdateView.as_view(), name='match_update'),
    path('matches/<uuid:pk>/finish/', views.MatchFinishView.as_view(), name='match_finish'),

    path('competitions/', views.CompetitionListView.as_view(), name='competition_list'),
    path('competitions/new/', views.CompetitionCreateView.as_view(), name='competition_create'),
    path('competitions/<uuid:pk>/edit/', views.CompetitionUpdateView.as_view(), name='competition_update'),

    path('leaderboard/', views.LeaderboardView.as_view(), name='leaderboard'),
]
