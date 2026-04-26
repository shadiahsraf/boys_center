from django.urls import path
from . import views

app_name = 'evaluations'

urlpatterns = [
    path('', views.EvaluationListView.as_view(), name='list'),
    path('new/', views.EvaluationCreateView.as_view(), name='create'),
    path('player/<uuid:player_id>/', views.PlayerEvaluationView.as_view(), name='player'),
]
