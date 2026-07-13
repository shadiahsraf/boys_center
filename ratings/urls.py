from django.urls import path
from . import views

app_name = 'ratings'

urlpatterns = [
    # ── Public (no login) ────────────────────────────────────────────
    path('', views.rate_index, name='index'),
    path('thanks/<int:facility_id>/', views.rate_thanks, name='thanks'),
    path('<int:facility_id>/', views.rate_facility, name='facility'),
    path('<int:facility_id>/submit/', views.rate_submit, name='submit'),

    # ── Admin / Coach-Manager only ───────────────────────────────────
    path('manage/', views.ManageFacilityList.as_view(), name='manage_list'),
    path('manage/dashboard/', views.Dashboard.as_view(), name='dashboard'),
    path('manage/dashboard/<int:facility_id>/',
         views.FacilityDashboard.as_view(), name='facility_dashboard'),
    path('manage/export.xlsx', views.ExportExcel.as_view(), name='export_excel'),

    path('manage/facility/new/', views.ManageFacilityForm.as_view(),
         name='manage_create'),
    path('manage/facility/<int:facility_id>/edit/',
         views.ManageFacilityForm.as_view(), name='manage_update'),
    path('manage/facility/<int:facility_id>/delete/',
         views.ManageFacilityDelete.as_view(), name='manage_delete'),
    path('manage/facility/<int:facility_id>/toggle/',
         views.manage_toggle_active, name='manage_toggle'),
]
