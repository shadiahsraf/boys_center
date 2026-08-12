import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from users.models import User


class CarouselSlide(models.Model):
    """A slide on the landing-page carousel. Admin uploads image + Arabic
    caption; English caption is optional."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title_ar = models.CharField(_('Title (Arabic)'), max_length=200)
    title_en = models.CharField(_('Title (English, optional)'), max_length=200, blank=True)
    description_ar = models.CharField(_('Description (Arabic)'), max_length=300, blank=True)
    description_en = models.CharField(_('Description (English, optional)'), max_length=300, blank=True)
    icon = models.CharField(
        _('Icon (emoji, optional)'), max_length=8, blank=True, default='',
        help_text=_('Optional emoji shown on top of the slide. Leave empty for a clean image.'),
    )
    image = models.ImageField(
        _('Image'), upload_to='carousel/', blank=True, null=True,
        help_text=_('The main content of the slide. Recommended: at least 1200x600 landscape.'),
    )
    tint_from = models.CharField(
        _('Fallback colour start'), max_length=9, default='#5A0F0F', blank=True,
        help_text=_('Only used if no image is uploaded. Hex colour, top-left.'),
    )
    tint_to = models.CharField(
        _('Fallback colour end'), max_length=9, default='#7A1C1C', blank=True,
        help_text=_('Only used if no image is uploaded. Hex colour, bottom-right.'),
    )
    order = models.PositiveIntegerField(_('Order'), default=0)
    is_active = models.BooleanField(_('Show on landing'), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'created_at']
        verbose_name = _('Carousel Slide')

    def __str__(self):
        return self.title_ar

    def title_for(self, lang='ar'):
        if lang == 'en' and self.title_en:
            return self.title_en
        return self.title_ar

    def description_for(self, lang='ar'):
        if lang == 'en' and self.description_en:
            return self.description_en
        return self.description_ar


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
