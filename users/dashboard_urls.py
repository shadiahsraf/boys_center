from django.urls import path
from .views import DashboardView

# This module shares the users namespace through include
urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
]
