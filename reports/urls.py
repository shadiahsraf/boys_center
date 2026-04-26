from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.ReportDashboardView.as_view(), name='dashboard'),
    path('attendance/', views.AttendanceReportView.as_view(), name='attendance'),
    path('attendance/pdf/', views.ExportAttendancePDFView.as_view(), name='export_attendance_pdf'),
    path('attendance/excel/', views.ExportAttendanceExcelView.as_view(), name='export_attendance_excel'),
    path('evaluations/excel/', views.ExportEvaluationsExcelView.as_view(), name='export_evaluations_excel'),
]
