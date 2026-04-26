from django.contrib import admin
from .models import Team, Match, CoachAssignment, TrainingSchedule, GoalRecord


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'sport', 'age_group', 'coach', 'member_count')
    list_filter = ('sport', 'age_group')
    search_fields = ('name',)
    filter_horizontal = ('members',)

    def member_count(self, obj):
        return obj.members.count()


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ('home_team', 'away_team', 'sport', 'scheduled_at', 'result', 'is_completed')
    list_filter = ('sport', 'is_completed', 'scheduled_at')
    search_fields = ('home_team__name', 'away_team__name', 'location')


admin.site.register(CoachAssignment)
admin.site.register(TrainingSchedule)
admin.site.register(GoalRecord)
