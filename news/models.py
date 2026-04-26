import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from users.models import User


class NewsPost(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(_('Title'), max_length=300)
    title_ar = models.CharField(_('Title (Arabic)'), max_length=300, blank=True)
    excerpt = models.CharField(_('Excerpt'), max_length=300, blank=True)
    content = models.TextField(_('Content'))
    content_ar = models.TextField(_('Content (Arabic)'), blank=True)
    image = models.ImageField(upload_to='news/', blank=True, null=True)
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    is_published = models.BooleanField(_('Is published'), default=True)
    is_featured = models.BooleanField(_('Featured'), default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('News Post')

    def __str__(self):
        return self.title

    def get_title(self, lang='en'):
        if lang == 'ar' and self.title_ar:
            return self.title_ar
        return self.title

    def get_content(self, lang='en'):
        if lang == 'ar' and self.content_ar:
            return self.content_ar
        return self.content
