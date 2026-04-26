from django.contrib import admin
from .models import Evaluation


@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    list_display = ('coach', 'player', 'sport', 'performance', 'behavior', 'commitment', 'average', 'created_at')
    list_filter = ('sport', 'created_at')
    search_fields = ('coach__first_name', 'coach__last_name', 'player__first_name', 'player__last_name')

    def average(self, obj):
        return obj.average
