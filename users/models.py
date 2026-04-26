import uuid
import qrcode
from io import BytesIO
from django.core.files import File
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


class Role(models.TextChoices):
    ADMIN = 'admin', _('Admin')
    COACH = 'coach', _('Coach')
    COACH_MANAGER = 'coach_manager', _('Coach Manager')
    PARENT = 'parent', _('Parent')
    YOUTH = 'youth', _('Youth')


class UserQuerySet(models.QuerySet):
    """SQLite-compatible role filtering. Uses string contains on JSON serialization."""
    def with_role(self, role):
        # JSON serialization wraps role with quotes: "admin"
        return self.filter(roles__icontains=f'"{role}"')


from django.contrib.auth.models import UserManager as DjangoUserManager
class UserManager(DjangoUserManager.from_queryset(UserQuerySet)):
    def with_role(self, role):
        return self.get_queryset().with_role(role)


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    objects = UserManager()
    member_code = models.CharField(max_length=20, unique=True, blank=True)
    roles = models.JSONField(default=list)
    phone = models.CharField(max_length=20, blank=True)
    photo = models.ImageField(upload_to='profiles/', blank=True, null=True)
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.TextField(blank=True)
    qr_code = models.ImageField(upload_to='qrcodes/', blank=True, null=True)
    parents = models.ManyToManyField('self', symmetrical=False, blank=True, related_name='children')
    created_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='created_users')
    # Coach-specific
    primary_sport = models.CharField(_('Primary sport'), max_length=30, blank=True,
                                     help_text=_('Which sport this coach mainly handles'))
    is_servant = models.BooleanField(_('Is servant (خادم)'), default=False,
                                     help_text=_('Volunteer servant role at the church'))

    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        ordering = ['first_name', 'last_name']

    def __str__(self):
        return self.get_full_name() or self.username

    def has_role(self, role):
        return role in (self.roles or [])

    @property
    def is_admin(self):
        return self.has_role(Role.ADMIN) or self.is_superuser

    @property
    def is_coach(self):
        return self.has_role(Role.COACH)

    @property
    def is_coach_manager(self):
        return self.has_role(Role.COACH_MANAGER) or self.is_admin

    @property
    def is_parent(self):
        return self.has_role(Role.PARENT)

    @property
    def is_youth(self):
        return self.has_role(Role.YOUTH)

    @property
    def role_display(self):
        if self.is_admin:
            return _('Admin')
        if self.is_coach_manager and not self.has_role(Role.ADMIN):
            return _('Coach Manager')
        if self.is_coach:
            sport = self.primary_sport.replace('_', ' ').title() if self.primary_sport else ''
            label = f'{sport} {_("Coach")}'.strip() if sport else _('Coach')
            if self.is_servant:
                label = f'{label} · {_("Servant")}'
            return label
        if self.is_parent:
            return _('Parent')
        if self.is_servant:
            return _('Servant')
        return _('Youth')

    @property
    def initials(self):
        if self.first_name and self.last_name:
            return f"{self.first_name[0]}{self.last_name[0]}".upper()
        return self.username[:2].upper()

    def get_absolute_url(self):
        return reverse('users:detail', kwargs={'pk': self.pk})

    def generate_qr_code(self):
        if not self.member_code:
            return
        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        qr.add_data(self.member_code)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#0f172a", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        self.qr_code.save(f'qr_{self.member_code}.png', File(buffer), save=False)

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        if not self.member_code:
            base = ''.join(c for c in (self.first_name[:2] + self.last_name[:2]).upper() if c.isalpha()) or 'BC'
            count = User.objects.filter(member_code__startswith=base).count()
            self.member_code = f"{base}{1000 + count + 1}"
        super().save(*args, **kwargs)
        if is_new and not self.qr_code:
            self.generate_qr_code()
            super().save(update_fields=['qr_code'])


class ActivityLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activity_logs')
    action = models.CharField(max_length=200)
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = _('Activity Log')
        verbose_name_plural = _('Activity Logs')

    def __str__(self):
        return f"{self.user} · {self.action} · {self.timestamp:%Y-%m-%d %H:%M}"
