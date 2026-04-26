from django import forms
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView

from users.mixins import RoleRequiredMixin
from users.models import Role
from .models import Event, EventType


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['title', 'event_type', 'description', 'start_datetime',
                  'end_datetime', 'location']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'tw-input'}),
            'event_type': forms.Select(attrs={'class': 'tw-input'}),
            'description': forms.Textarea(attrs={'class': 'tw-input', 'rows': 3}),
            'start_datetime': forms.DateTimeInput(attrs={'class': 'tw-input', 'type': 'datetime-local'}),
            'end_datetime': forms.DateTimeInput(attrs={'class': 'tw-input', 'type': 'datetime-local'}),
            'location': forms.TextInput(attrs={'class': 'tw-input'}),
        }


class EventListView(ListView):
    model = Event
    template_name = 'events/event_list.html'
    context_object_name = 'events'

    def get_queryset(self):
        qs = Event.objects.all()
        event_type = self.request.GET.get('type')
        when = self.request.GET.get('when', 'upcoming')
        if event_type:
            qs = qs.filter(event_type=event_type)
        if when == 'upcoming':
            qs = qs.filter(start_datetime__gte=timezone.now()).order_by('start_datetime')
        elif when == 'past':
            qs = qs.filter(start_datetime__lt=timezone.now()).order_by('-start_datetime')
        else:
            qs = qs.order_by('start_datetime')
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['event_types'] = EventType.choices
        ctx['filter_type'] = self.request.GET.get('type', '')
        ctx['filter_when'] = self.request.GET.get('when', 'upcoming')
        return ctx


class EventDetailView(DetailView):
    model = Event
    template_name = 'events/event_detail.html'


class EventCreateView(RoleRequiredMixin, CreateView):
    required_roles = [Role.ADMIN, Role.COACH_MANAGER]
    model = Event
    form_class = EventForm
    template_name = 'events/event_form.html'
    success_url = reverse_lazy('events:list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, _('Event created.'))
        return super().form_valid(form)


class EventUpdateView(RoleRequiredMixin, UpdateView):
    required_roles = [Role.ADMIN, Role.COACH_MANAGER]
    model = Event
    form_class = EventForm
    template_name = 'events/event_form.html'
    success_url = reverse_lazy('events:list')


class EventDeleteView(RoleRequiredMixin, DeleteView):
    required_roles = [Role.ADMIN, Role.COACH_MANAGER]
    model = Event
    template_name = 'events/event_confirm_delete.html'
    success_url = reverse_lazy('events:list')

    def form_valid(self, form):
        from django.contrib import messages as msgs
        from users.mixins import log_action
        log_action(self.request.user, 'event_deleted',
                   {'title': self.object.title}, self.request)
        msgs.success(self.request, _("Event deleted."))
        return super().form_valid(form)
