from django.urls import path
from . import views

app_name = 'quiz'

urlpatterns = [
    path('', views.QuizDayView.as_view(), name='today'),
    path('answer/', views.submit_answer, name='submit_answer'),
]
