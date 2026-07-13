from django.contrib import admin
from .models import Facility, RatingQuestion, Submission, Answer


class RatingQuestionInline(admin.TabularInline):
    model = RatingQuestion
    extra = 1


class AnswerInline(admin.TabularInline):
    model = Answer
    readonly_fields = ('question', 'stars')
    extra = 0
    can_delete = False


@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'order', 'submission_count', 'average_overall')
    list_filter = ('is_active',)
    list_editable = ('is_active', 'order')
    search_fields = ('name', 'description')
    inlines = [RatingQuestionInline]


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('facility', 'visitor_name', 'average_stars', 'submitted_at', 'ip_address')
    list_filter = ('facility', 'submitted_at')
    readonly_fields = ('facility', 'visitor_name', 'comment', 'session_key',
                       'ip_address', 'user_agent', 'submitted_at')
    inlines = [AnswerInline]
    date_hierarchy = 'submitted_at'
