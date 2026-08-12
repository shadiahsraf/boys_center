from django import forms
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView

from users.mixins import RoleRequiredMixin
from users.models import Role
from .models import CarouselSlide, NewsPost


class NewsForm(forms.ModelForm):
    """Arabic-first news form. Arabic fields are required; English is optional."""

    class Meta:
        model = NewsPost
        fields = ['title_ar', 'content_ar', 'title', 'excerpt', 'content',
                  'image', 'is_published', 'is_featured']
        widgets = {
            # Arabic — primary
            'title_ar': forms.TextInput(attrs={
                'class': 'tw-input', 'dir': 'rtl', 'lang': 'ar',
                'placeholder': 'عنوان الخبر بالعربية',
            }),
            'content_ar': forms.Textarea(attrs={
                'class': 'tw-input', 'rows': 8, 'dir': 'rtl', 'lang': 'ar',
                'placeholder': 'اكتب نص الخبر بالعربية…',
            }),
            # English — optional
            'title': forms.TextInput(attrs={
                'class': 'tw-input',
                'placeholder': 'Optional English title',
            }),
            'excerpt': forms.TextInput(attrs={
                'class': 'tw-input',
                'placeholder': _('Short summary shown in cards (optional)'),
            }),
            'content': forms.Textarea(attrs={
                'class': 'tw-input', 'rows': 6,
                'placeholder': 'Optional English content',
            }),
            'image': forms.ClearableFileInput(attrs={'class': 'tw-input-file'}),
            'is_published': forms.CheckboxInput(attrs={'class': 'tw-checkbox'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'tw-checkbox'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Arabic fields are required, English are optional
        self.fields['title_ar'].required = True
        self.fields['content_ar'].required = True
        self.fields['title_ar'].label = _('Title (Arabic)')
        self.fields['content_ar'].label = _('Content (Arabic)')
        for f in ('title', 'excerpt', 'content'):
            self.fields[f].required = False

    def clean(self):
        cleaned = super().clean()
        # If admin didn't supply English title/content, fall back to Arabic so
        # get_title/get_content and English-locale visitors still see something
        # (the fallback is Arabic text — better than nothing).
        if not cleaned.get('title'):
            cleaned['title'] = cleaned.get('title_ar', '')
        if not cleaned.get('content'):
            cleaned['content'] = cleaned.get('content_ar', '')
        return cleaned


class NewsListView(ListView):
    model = NewsPost
    template_name = 'news/news_list.html'
    context_object_name = 'posts'
    paginate_by = 12

    def get_queryset(self):
        return NewsPost.objects.filter(is_published=True).select_related('author')


class NewsDetailView(DetailView):
    model = NewsPost
    template_name = 'news/news_detail.html'
    context_object_name = 'post'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['related'] = NewsPost.objects.filter(is_published=True).exclude(pk=self.object.pk)[:3]
        return ctx


class NewsCreateView(RoleRequiredMixin, CreateView):
    required_roles = [Role.ADMIN]
    model = NewsPost
    form_class = NewsForm
    template_name = 'news/news_form.html'
    success_url = reverse_lazy('news:list')

    def form_valid(self, form):
        form.instance.author = self.request.user
        messages.success(self.request, _('News post published.'))
        return super().form_valid(form)


class NewsUpdateView(RoleRequiredMixin, UpdateView):
    required_roles = [Role.ADMIN]
    model = NewsPost
    form_class = NewsForm
    template_name = 'news/news_form.html'
    success_url = reverse_lazy('news:list')


class NewsDeleteView(RoleRequiredMixin, DeleteView):
    required_roles = [Role.ADMIN]
    model = NewsPost
    success_url = reverse_lazy('news:list')
    template_name = 'news/news_confirm_delete.html'

    def form_valid(self, form):
        from users.mixins import log_action
        log_action(self.request.user, 'news_deleted',
                   {'title': self.object.title}, self.request)
        messages.success(self.request, _("Post deleted."))
        return super().form_valid(form)


# ─── CAROUSEL SLIDES ────────────────────────────────────────────────────────

class CarouselSlideForm(forms.ModelForm):
    class Meta:
        model = CarouselSlide
        fields = ['title_ar', 'title_en', 'description_ar', 'description_en',
                  'icon', 'image', 'tint_from', 'tint_to', 'order', 'is_active']
        widgets = {
            'title_ar': forms.TextInput(attrs={
                'class': 'tw-input', 'dir': 'rtl', 'lang': 'ar',
                'placeholder': 'مثلاً: كرة القدم',
            }),
            'title_en': forms.TextInput(attrs={
                'class': 'tw-input',
                'placeholder': 'Optional English title',
            }),
            'description_ar': forms.TextInput(attrs={
                'class': 'tw-input', 'dir': 'rtl', 'lang': 'ar',
                'placeholder': 'تدريبات ومباريات لكل الفئات العمرية',
            }),
            'description_en': forms.TextInput(attrs={
                'class': 'tw-input',
                'placeholder': 'Optional English description',
            }),
            'icon': forms.TextInput(attrs={
                'class': 'tw-input',
                'style': 'font-size:22px;max-width:100px;text-align:center;',
                'maxlength': 8,
            }),
            'image': forms.ClearableFileInput(attrs={'class': 'tw-input-file'}),
            'tint_from': forms.TextInput(attrs={'type': 'color', 'class': 'tw-input',
                                                'style': 'width:80px;height:44px;padding:2px;'}),
            'tint_to': forms.TextInput(attrs={'type': 'color', 'class': 'tw-input',
                                              'style': 'width:80px;height:44px;padding:2px;'}),
            'order': forms.NumberInput(attrs={'class': 'tw-input', 'style': 'max-width:120px;'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'tw-checkbox'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['title_ar'].required = True


class CarouselListView(RoleRequiredMixin, ListView):
    required_roles = [Role.ADMIN, Role.COACH_MANAGER]
    model = CarouselSlide
    template_name = 'news/carousel_list.html'
    context_object_name = 'slides'


class CarouselCreateView(RoleRequiredMixin, CreateView):
    required_roles = [Role.ADMIN, Role.COACH_MANAGER]
    model = CarouselSlide
    form_class = CarouselSlideForm
    template_name = 'news/carousel_form.html'
    success_url = reverse_lazy('news:carousel_list')

    def form_valid(self, form):
        messages.success(self.request, _('Slide added to the carousel.'))
        return super().form_valid(form)


class CarouselUpdateView(RoleRequiredMixin, UpdateView):
    required_roles = [Role.ADMIN, Role.COACH_MANAGER]
    model = CarouselSlide
    form_class = CarouselSlideForm
    template_name = 'news/carousel_form.html'
    success_url = reverse_lazy('news:carousel_list')

    def form_valid(self, form):
        messages.success(self.request, _('Slide updated.'))
        return super().form_valid(form)


class CarouselDeleteView(RoleRequiredMixin, DeleteView):
    required_roles = [Role.ADMIN, Role.COACH_MANAGER]
    model = CarouselSlide
    success_url = reverse_lazy('news:carousel_list')
    template_name = 'news/carousel_confirm_delete.html'

    def form_valid(self, form):
        messages.success(self.request, _('Slide deleted.'))
        return super().form_valid(form)
