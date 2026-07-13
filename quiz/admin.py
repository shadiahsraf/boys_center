from django.contrib import admin
from .models import BibleQuestion, DailyQuizAttempt, UserStreak


@admin.register(BibleQuestion)
class BibleQuestionAdmin(admin.ModelAdmin):
    list_display = ('text_short', 'correct', 'reference', 'is_active', 'created_at')
    list_filter = ('is_active', 'correct')
    search_fields = ('text', 'reference')

    def text_short(self, obj):
        return obj.text[:60]
    text_short.short_description = 'سؤال'


@admin.register(UserStreak)
class UserStreakAdmin(admin.ModelAdmin):
    list_display = ('user', 'current_streak', 'best_streak', 'total_days_completed', 'last_completed_day')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
    readonly_fields = ('updated_at',)


@admin.register(DailyQuizAttempt)
class DailyQuizAttemptAdmin(admin.ModelAdmin):
    list_display = ('user', 'day', 'question', 'answer', 'is_correct', 'answered_at')
    list_filter = ('day', 'is_correct')
    search_fields = ('user__username',)
    readonly_fields = ('answered_at',)
