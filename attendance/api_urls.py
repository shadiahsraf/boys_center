from django.urls import path
from . import views

app_name = 'attendance_api'

urlpatterns = [
    path('session/<uuid:pk>/records/', views.SessionRecordsAPIView.as_view(), name='session_records'),
]
