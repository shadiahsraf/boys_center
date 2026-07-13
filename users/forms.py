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


# Roles offered to admins in the user-create / user-edit form.
# `Role.PARENT` is intentionally excluded — parent contact info now lives on
# the player's own profile (one account per family). Existing parent accounts
# in the DB keep working; we just don't expose the role to NEW creations.
ASSIGNABLE_ROLE_CHOICES = [
    (r.value, r.label) for r in Role if r != Role.PARENT
]


# Arabic-first error messages applied to all forms via Meta.error_messages.
COMMON_ERRORS = {
    'required': _('This field is required.'),
    'invalid':  _('Please enter a valid value.'),
}


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'tw-input',
            'placeholder': _('Username'),
            'autofocus': True,
        }),
        error_messages=COMMON_ERRORS,
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'tw-input',
            'placeholder': _('Password'),
        }),
        error_messages=COMMON_ERRORS,
    )
    error_messages = {
        'invalid_login': _('Please enter a correct username and password. Note that both fields may be case-sensitive.'),
        'inactive': _('This account is inactive.'),
    }


class _UserBase(forms.ModelForm):
    """Shared logic for Create + Update forms — roles, children, primary sport, servant, parent contact."""
    roles = forms.MultipleChoiceField(
        choices=ASSIGNABLE_ROLE_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=True,
        error_messages={
            'required': _('Please select at least one role.'),
        },
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
    # Parent contact — shown for youth members; fields live on User itself
    parent_name = forms.CharField(
        label=_('Parent name'),
        required=False,
        widget=forms.TextInput(attrs={'class': 'tw-input'}),
    )
    parent_phone = forms.CharField(
        label=_('Parent phone'),
        required=False,
        widget=forms.TextInput(attrs={'class': 'tw-input'}),
    )
    parent_email = forms.EmailField(
        label=_('Parent email'),
        required=False,
        widget=forms.EmailInput(attrs={'class': 'tw-input'}),
        error_messages={'invalid': _('Please enter a valid email address.')},
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['primary_sport'].widget.attrs.update({'class': 'tw-input'})
        # Pre-fill parent contact when editing
        if self.instance and self.instance.pk:
            self.fields['parent_name'].initial = self.instance.parent_name
            self.fields['parent_phone'].initial = self.instance.parent_phone
            self.fields['parent_email'].initial = self.instance.parent_email

    def clean_roles(self):
        return list(self.cleaned_data['roles'])

    def clean(self):
        cleaned = super().clean()
        roles = cleaned.get('roles', [])
        if Role.COACH not in roles:
            cleaned['primary_sport'] = ''
        # Parent contact fields only meaningful for youth members
        if Role.YOUTH not in roles:
            cleaned['parent_name'] = ''
            cleaned['parent_phone'] = ''
            cleaned['parent_email'] = ''
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.primary_sport = self.cleaned_data.get('primary_sport') or ''
        user.is_servant = self.cleaned_data.get('is_servant', False)
        user.parent_name = self.cleaned_data.get('parent_name', '') or ''
        user.parent_phone = self.cleaned_data.get('parent_phone', '') or ''
        user.parent_email = self.cleaned_data.get('parent_email', '') or ''
        if commit:
            user.save()
            self.save_m2m()
        return user


class UserCreateForm(_UserBase):
    password1 = forms.CharField(
        label=_('Password'),
        widget=forms.PasswordInput(attrs={'class': 'tw-input'}),
        error_messages=COMMON_ERRORS,
    )
    password2 = forms.CharField(
        label=_('Confirm Password'),
        widget=forms.PasswordInput(attrs={'class': 'tw-input'}),
        error_messages=COMMON_ERRORS,
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
        error_messages = {
            'username':   {'required': _('Username is required.'),
                           'unique': _('A user with that username already exists.')},
            'first_name': {'required': _('First name is required.')},
            'last_name':  {'required': _('Last name is required.')},
            'email':      {'invalid':  _('Please enter a valid email address.')},
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
            self.save_m2m()
            # _UserBase.save handled parent_* + sport already via cleaned_data on the in-memory instance
            user.parent_name = self.cleaned_data.get('parent_name', '') or ''
            user.parent_phone = self.cleaned_data.get('parent_phone', '') or ''
            user.parent_email = self.cleaned_data.get('parent_email', '') or ''
            user.primary_sport = self.cleaned_data.get('primary_sport') or ''
            user.is_servant = self.cleaned_data.get('is_servant', False)
            user.save()
        return user


class ProfilePhotoForm(forms.ModelForm):
    """Lightweight form that lets ANY logged-in user change just their own photo."""
    class Meta:
        model = User
        fields = ['photo']
        widgets = {
            'photo': forms.ClearableFileInput(attrs={
                'class': 'tw-input-file',
                'accept': 'image/*',
            }),
        }
        error_messages = {
            'photo': {'invalid': _('Please choose a valid image file.')},
        }

    def clean_photo(self):
        photo = self.cleaned_data.get('photo')
        if photo and hasattr(photo, 'size') and photo.size > 5 * 1024 * 1024:
            raise forms.ValidationError(_('Image is too large (max 5 MB).'))
        return photo


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
        error_messages = {
            'first_name': {'required': _('First name is required.')},
            'last_name':  {'required': _('Last name is required.')},
            'email':      {'invalid':  _('Please enter a valid email address.')},
        }


class ProfileSelfUpdateForm(forms.ModelForm):
    """
    Self-service profile editing for any logged-in user.
    Lets a player update their own contact info AND their parent's contact info,
    since the player and parent share one account.
    """
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'address',
                  'parent_name', 'parent_phone', 'parent_email']
        widgets = {
            'first_name':   forms.TextInput(attrs={'class': 'tw-input'}),
            'last_name':    forms.TextInput(attrs={'class': 'tw-input'}),
            'email':        forms.EmailInput(attrs={'class': 'tw-input'}),
            'phone':        forms.TextInput(attrs={'class': 'tw-input'}),
            'address':      forms.Textarea(attrs={'class': 'tw-input', 'rows': 2}),
            'parent_name':  forms.TextInput(attrs={'class': 'tw-input'}),
            'parent_phone': forms.TextInput(attrs={'class': 'tw-input'}),
            'parent_email': forms.EmailInput(attrs={'class': 'tw-input'}),
        }
        error_messages = {
            'first_name': {'required': _('First name is required.')},
            'last_name':  {'required': _('Last name is required.')},
            'email':      {'invalid':  _('Please enter a valid email address.')},
            'parent_email': {'invalid': _('Please enter a valid email address.')},
        }
