from django.urls import path
from . import views

app_name = 'dailychallenge'

urlpatterns = [
    # ── Solver flow (youth) ───────────────────────────────────────────
    path('', views.DailyChallengeView.as_view(), name='today'),
    path('submit/', views.submit_challenge, name='submit'),

    # ── Management flow (admin / coach-manager) ───────────────────────
    path('manage/',                   views.ManageListView.as_view(),   name='manage_list'),
    path('manage/new/',               views.ManageCreateView.as_view(), name='manage_create'),
    path('manage/<int:pk>/edit/',     views.ManageUpdateView.as_view(), name='manage_update'),
    path('manage/<int:pk>/delete/',   views.ManageDeleteView.as_view(), name='manage_delete'),
]
