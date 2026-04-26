from django.contrib import admin
from .models import Event, ParentActivity


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'event_type', 'start_datetime', 'location', 'created_by')
    list_filter = ('event_type', 'start_datetime')
    search_fields = ('title', 'location', 'description')


admin.site.register(ParentActivity)
