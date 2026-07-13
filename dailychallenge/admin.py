from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import (DailyContent, Question, Choice,
                     ChallengeProgress, ChallengeAnswer)


# ── Choice inline (4 per question, exactly one marked correct) ──────────────
class ChoiceInlineFormset(forms.BaseInlineFormSet):
    def clean(self):
        super().clean()
        correct = 0
        filled = 0
        for form in self.forms:
            if not hasattr(form, 'cleaned_data'):
                continue
            cd = form.cleaned_data
            if cd.get('DELETE'):
                continue
            if cd.get('text'):
                filled += 1
                if cd.get('is_correct'):
                    correct += 1
        # Only validate when the admin actually added choices
        if filled and correct != 1:
            raise ValidationError(
                _('Each question must have exactly ONE correct choice (found %(n)d).')
                % {'n': correct}
            )


class ChoiceInline(admin.TabularInline):
    model = Choice
    formset = ChoiceInlineFormset
    extra = 4
    min_num = 2
    max_num = 6


class QuestionInline(admin.StackedInline):
    model = Question
    extra = 3
    show_change_link = True
    fields = ('order', 'text')


@admin.register(DailyContent)
class DailyContentAdmin(admin.ModelAdmin):
    list_display = ('date', 'bible_reference', 'question_count', 'is_published', 'preview_link')
    list_filter = ('is_published',)
    search_fields = ('bible_reference',)
    date_hierarchy = 'date'
    inlines = [QuestionInline]
    # `date` is unique=True on the model, so duplicate dates are rejected
    # automatically with a clear validation error.

    @admin.display(description=_('Questions'))
    def question_count(self, obj):
        return obj.questions.count()

    @admin.display(description=_('Preview'))
    def preview_link(self, obj):
        url = reverse('dailychallenge:today') + f'?date={obj.date.isoformat()}'
        return format_html('<a href="{}" target="_blank">👁 {}</a>', url, _('Preview'))


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'daily_content', 'order')
    list_filter = ('daily_content__date',)
    search_fields = ('text',)
    inlines = [ChoiceInline]


@admin.register(ChallengeProgress)
class ChallengeProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'streak_count', 'best_streak', 'total_completed', 'last_completed_date')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
    readonly_fields = ('updated_at',)


@admin.register(ChallengeAnswer)
class ChallengeAnswerAdmin(admin.ModelAdmin):
    list_display = ('user', 'daily_content', 'question', 'selected_choice', 'is_correct', 'created_at')
    list_filter = ('is_correct', 'daily_content__date')
    search_fields = ('user__username',)
    readonly_fields = ('created_at',)
