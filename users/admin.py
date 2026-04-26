from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, ActivityLog


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'get_full_name', 'member_code', 'email',
                    'display_roles', 'is_active', 'date_joined')
    list_filter = ('is_active', 'is_staff', 'date_joined')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'member_code', 'phone')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Boys Center', {
            'fields': ('member_code', 'roles', 'phone', 'photo', 'date_of_birth',
                       'address', 'parents', 'qr_code')
        }),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Boys Center', {
            'fields': ('roles', 'first_name', 'last_name', 'email', 'phone')
        }),
    )
    filter_horizontal = ('parents', 'groups', 'user_permissions')
    readonly_fields = ('member_code', 'qr_code')

    def display_roles(self, obj):
        return ', '.join(obj.roles or [])
    display_roles.short_description = 'Roles'


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'ip_address', 'timestamp')
    list_filter = ('action', 'timestamp')
    search_fields = ('user__username', 'user__first_name', 'action')
    readonly_fields = ('timestamp',)
