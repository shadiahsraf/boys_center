from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext_lazy as _
from .models import User, Role


SPORT_CHOICES_FOR_FORM = [
    ('', _('— select sport —')),
    ('football', _('Football')),
    ('basketball', _('Basketball')),
    ('volleyball', _('Volleyball')),
    ('handball', _('Handball')),
    ('table_tennis', _('Table Tennis')),
]


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'tw-input',
            'placeholder': _('Username'),
            'autofocus': True,
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'tw-input',
            'placeholder': _('Password'),
        })
    )


class _UserBase(forms.ModelForm):
    """Shared logic for Create + Update forms — roles, children, primary sport, servant."""
    roles = forms.MultipleChoiceField(
        choices=[(r.value, r.label) for r in Role],
        widget=forms.CheckboxSelectMultiple,
        required=True,
    )
    primary_sport = forms.ChoiceField(
        label=_('Primary sport (for coaches)'),
        choices=SPORT_CHOICES_FOR_FORM,
        required=False,
    )
    is_servant = forms.BooleanField(
        label=_('Is servant (خادم)'),
        required=False,
    )
    children = forms.ModelMultipleChoiceField(
        label=_('Children to link (for parents)'),
        queryset=User.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'tw-input', 'size': 8}),
        help_text=_('Hold Ctrl/Cmd to select multiple. Only youth members appear here.'),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['children'].queryset = User.objects.with_role('youth').order_by('first_name', 'last_name')
        self.fields['primary_sport'].widget.attrs.update({'class': 'tw-input'})
        # Pre-fill children for editing
        if self.instance.pk:
            self.fields['children'].initial = self.instance.children.all()

    def clean_roles(self):
        return list(self.cleaned_data['roles'])

    def clean(self):
        cleaned = super().clean()
        roles = cleaned.get('roles', [])
        # If parent role selected, at least 0 children is fine (optional)
        # If coach role selected and primary_sport is empty, that's also OK (legacy)
        # If parent role NOT selected but children chosen, ignore the children
        if Role.PARENT not in roles:
            cleaned['children'] = User.objects.none()
        # Same for sport / servant — clear them out if irrelevant
        if Role.COACH not in roles:
            cleaned['primary_sport'] = ''
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.primary_sport = self.cleaned_data.get('primary_sport') or ''
        user.is_servant = self.cleaned_data.get('is_servant', False)
        if commit:
            user.save()
            self._save_children(user)
            self.save_m2m()
        return user

    def _save_children(self, user):
        """For parent users — link selected children's parents M2M."""
        chosen = self.cleaned_data.get('children')
        if chosen is None:
            return
        # Clear previous parent links from this user, then re-add
        existing_children = list(user.children.all())
        for child in existing_children:
            if child not in chosen:
                child.parents.remove(user)
        for child in chosen:
            child.parents.add(user)


class UserCreateForm(_UserBase):
    password1 = forms.CharField(
        label=_('Password'),
        widget=forms.PasswordInput(attrs={'class': 'tw-input'})
    )
    password2 = forms.CharField(
        label=_('Confirm Password'),
        widget=forms.PasswordInput(attrs={'class': 'tw-input'})
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'phone',
                  'date_of_birth', 'address', 'photo', 'roles']
        widgets = {
            'username':       forms.TextInput(attrs={'class': 'tw-input'}),
            'first_name':     forms.TextInput(attrs={'class': 'tw-input'}),
            'last_name':      forms.TextInput(attrs={'class': 'tw-input'}),
            'email':          forms.EmailInput(attrs={'class': 'tw-input'}),
            'phone':          forms.TextInput(attrs={'class': 'tw-input'}),
            'date_of_birth':  forms.DateInput(attrs={'class': 'tw-input', 'type': 'date'}),
            'address':        forms.Textarea(attrs={'class': 'tw-input', 'rows': 2}),
            'photo':          forms.ClearableFileInput(attrs={'class': 'tw-input-file'}),
        }

    def clean_password2(self):
        p1 = self.cleaned_data.get('password1')
        p2 = self.cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError(_('Passwords do not match.'))
        return p2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
            self._save_children(user)
            self.save_m2m()
        return user


class UserUpdateForm(_UserBase):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone',
                  'date_of_birth', 'address', 'photo', 'roles', 'is_active']
        widgets = {
            'first_name':     forms.TextInput(attrs={'class': 'tw-input'}),
            'last_name':      forms.TextInput(attrs={'class': 'tw-input'}),
            'email':          forms.EmailInput(attrs={'class': 'tw-input'}),
            'phone':          forms.TextInput(attrs={'class': 'tw-input'}),
            'date_of_birth':  forms.DateInput(attrs={'class': 'tw-input', 'type': 'date'}),
            'address':        forms.Textarea(attrs={'class': 'tw-input', 'rows': 2}),
            'photo':          forms.ClearableFileInput(attrs={'class': 'tw-input-file'}),
            'is_active':      forms.CheckboxInput(attrs={'class': 'tw-checkbox'}),
        }
