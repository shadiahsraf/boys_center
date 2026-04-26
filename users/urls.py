from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('', views.UserListView.as_view(), name='list'),
    path('new/', views.UserCreateView.as_view(), name='create'),
    path('<uuid:pk>/', views.UserDetailView.as_view(), name='detail'),
    path('<uuid:pk>/edit/', views.UserUpdateView.as_view(), name='update'),
    path('<uuid:pk>/delete/', views.UserDeleteView.as_view(), name='delete'),
    path('activity-log/', views.ActivityLogView.as_view(), name='activity_log'),
]
