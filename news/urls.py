from django.urls import path
from . import views

app_name = 'news'

urlpatterns = [
    path('', views.NewsListView.as_view(), name='list'),
    path('new/', views.NewsCreateView.as_view(), name='create'),

    # Carousel management (before uuid patterns so it doesn't get matched)
    path('carousel/', views.CarouselListView.as_view(), name='carousel_list'),
    path('carousel/new/', views.CarouselCreateView.as_view(), name='carousel_create'),
    path('carousel/<uuid:pk>/edit/', views.CarouselUpdateView.as_view(), name='carousel_update'),
    path('carousel/<uuid:pk>/delete/', views.CarouselDeleteView.as_view(), name='carousel_delete'),

    path('<uuid:pk>/', views.NewsDetailView.as_view(), name='detail'),
    path('<uuid:pk>/edit/', views.NewsUpdateView.as_view(), name='update'),
    path('<uuid:pk>/delete/', views.NewsDeleteView.as_view(), name='delete'),
]
