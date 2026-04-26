from django.urls import path
from . import views

app_name = 'attendance'

urlpatterns = [
    path('', views.SessionListView.as_view(), name='list'),
    path('new/', views.SessionCreateView.as_view(), name='create'),
    path('<uuid:pk>/', views.SessionDetailView.as_view(), name='detail'),
    path('<uuid:pk>/toggle/', views.SessionToggleView.as_view(), name='toggle'),
    path('<uuid:pk>/manual/', views.ManualCheckInView.as_view(), name='manual_checkin'),
    path('check-in/<str:token>/', views.CheckInLandingView.as_view(), name='check_in'),
]
