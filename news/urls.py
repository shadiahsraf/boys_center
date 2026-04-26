from django.urls import path
from . import views

app_name = 'news'

urlpatterns = [
    path('', views.NewsListView.as_view(), name='list'),
    path('new/', views.NewsCreateView.as_view(), name='create'),
    path('<uuid:pk>/', views.NewsDetailView.as_view(), name='detail'),
    path('<uuid:pk>/edit/', views.NewsUpdateView.as_view(), name='update'),
    path('<uuid:pk>/delete/', views.NewsDeleteView.as_view(), name='delete'),
]
