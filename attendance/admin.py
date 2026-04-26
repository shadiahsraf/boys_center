from django.contrib import admin
from .models import AttendanceSession, AttendanceRecord


class AttendanceRecordInline(admin.TabularInline):
    model = AttendanceRecord
    extra = 0
    readonly_fields = ('check_in_time',)


@admin.register(AttendanceSession)
class AttendanceSessionAdmin(admin.ModelAdmin):
    list_display = ('title', 'session_type', 'sport', 'date', 'coach',
                    'attendance_count', 'is_open', 'is_expired')
    list_filter = ('session_type', 'sport', 'is_open', 'date')
    search_fields = ('title', 'location', 'coach__first_name', 'coach__last_name')
    inlines = [AttendanceRecordInline]
    readonly_fields = ('token', 'qr_code', 'created_at')


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ('user', 'session', 'status', 'check_in_time')
    list_filter = ('status', 'session__session_type')
    search_fields = ('user__first_name', 'user__last_name', 'user__member_code')
    readonly_fields = ('check_in_time',)
