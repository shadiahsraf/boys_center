from django import forms
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView

from users.mixins import RoleRequiredMixin
from users.models import Role
from .models import NewsPost


class NewsForm(forms.ModelForm):
    class Meta:
        model = NewsPost
        fields = ['title', 'title_ar', 'excerpt', 'content', 'content_ar',
                  'image', 'is_published', 'is_featured']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'tw-input'}),
            'title_ar': forms.TextInput(attrs={'class': 'tw-input', 'dir': 'rtl'}),
            'excerpt': forms.TextInput(attrs={'class': 'tw-input',
                                              'placeholder': _('Short summary shown in cards...')}),
            'content': forms.Textarea(attrs={'class': 'tw-input', 'rows': 6}),
            'content_ar': forms.Textarea(attrs={'class': 'tw-input', 'rows': 6, 'dir': 'rtl'}),
            'image': forms.ClearableFileInput(attrs={'class': 'tw-input-file'}),
            'is_published': forms.CheckboxInput(attrs={'class': 'tw-checkbox'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'tw-checkbox'}),
        }


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
