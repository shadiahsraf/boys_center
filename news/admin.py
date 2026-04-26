from django.contrib import admin
from .models import NewsPost


@admin.register(NewsPost)
class NewsPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'is_published', 'is_featured', 'created_at')
    list_filter = ('is_published', 'is_featured', 'created_at')
    search_fields = ('title', 'content')
