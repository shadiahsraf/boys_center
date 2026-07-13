from django.contrib import admin
from .models import (Team, Match, CoachAssignment, TrainingSchedule,
                     GoalRecord, Competition)


@admin.register(Competition)
class CompetitionAdmin(admin.ModelAdmin):
    list_display = ('name', 'competition_type', 'sport', 'season', 'is_active')
    list_filter = ('competition_type', 'sport', 'is_active')
    search_fields = ('name', 'season')


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
    list_display = ('home_team', 'away_team', 'sport', 'competition', 'scheduled_at', 'result', 'is_completed')
    list_filter = ('sport', 'competition', 'is_completed', 'scheduled_at')
    search_fields = ('home_team__name', 'away_team__name', 'location')


admin.site.register(CoachAssignment)
admin.site.register(TrainingSchedule)
admin.site.register(GoalRecord)
