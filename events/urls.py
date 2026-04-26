from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    path('', views.EventListView.as_view(), name='list'),
    path('new/', views.EventCreateView.as_view(), name='create'),
    path('<uuid:pk>/', views.EventDetailView.as_view(), name='detail'),
    path('<uuid:pk>/edit/', views.EventUpdateView.as_view(), name='update'),
    path('<uuid:pk>/delete/', views.EventDeleteView.as_view(), name='delete'),
]
