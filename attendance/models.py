import uuid
import secrets
import qrcode
from io import BytesIO
from django.core.files.base import ContentFile
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from users.models import User


class SessionType(models.TextChoices):
    TRAINING = 'training', _('Training')
    PRAYER = 'prayer', _('Prayer Meeting')
    MATCH = 'match', _('Match')
    EVENT = 'event', _('Event')


class AttendanceSession(models.Model):
    """
    A session with a unique token-based QR.
    Coach creates session → QR is generated containing the token →
    Players scan QR + enter their member code → attendance recorded.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(_('Title'), max_length=200)
    session_type = models.CharField(_('Type'), max_length=20, choices=SessionType.choices)
    sport = models.CharField(_('Sport'), max_length=30, blank=True)
    coach = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                              related_name='conducted_sessions')
    token = models.CharField(_('Token'), max_length=40, unique=True, editable=False)
    date = models.DateField(_('Date'))
    start_time = models.TimeField(_('Start time'))
    end_time = models.TimeField(_('End time'), null=True, blank=True)
    location = models.CharField(_('Location'), max_length=200)
    expires_at = models.DateTimeField(_('Expires at'), null=True, blank=True,
                                      help_text=_('After this time the QR is invalid'))
    is_open = models.BooleanField(_('Is open'), default=True)
    qr_code = models.ImageField(upload_to='session_qrcodes/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-start_time']
        verbose_name = _('Attendance Session')

    def __str__(self):
        return f"{self.title} — {self.date}"

    @property
    def is_expired(self):
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at

    @property
    def is_active(self):
        return self.is_open and not self.is_expired

    @property
    def attendance_count(self):
        return self.records.count()

    def generate_qr(self, base_url=None):
        """
        Generate QR pointing to the check-in page.
        `base_url` overrides the default; if not given we look at the
        DJANGO_QR_BASE_URL env var (so admins can set it to the public LAN/HTTPS
        URL the phones can reach). Fallback is the relative path, which works
        when the user opens the URL on the same host that served the QR.
        """
        import os as _os
        from django.conf import settings as _settings
        base = base_url
        if base is None:
            base = _os.environ.get('DJANGO_QR_BASE_URL', '').rstrip('/')
        # The site is Arabic-first; the URL is localized.
        lang_prefix = getattr(_settings, 'LANGUAGE_CODE', 'ar') or 'ar'
        check_in_url = f"{base}/{lang_prefix}/attendance/check-in/{self.token}/"
        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        qr.add_data(check_in_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#0f172a", back_color="white")
        buf = BytesIO()
        img.save(buf, format='PNG')
        self.qr_code.save(f'session_{self.token}.png', ContentFile(buf.getvalue()), save=False)

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(16)
        # Set expiry default = end_time on same date (or 4 hours after start)
        if not self.expires_at and self.date and self.start_time:
            from datetime import datetime, timedelta
            naive = datetime.combine(self.date, self.end_time or self.start_time)
            self.expires_at = timezone.make_aware(naive + timedelta(hours=2))
        super().save(*args, **kwargs)
        if not self.qr_code:
            self.generate_qr()
            super().save(update_fields=['qr_code'])


class AttendanceRecord(models.Model):
    STATUS_CHOICES = [
        ('present', _('Present')),
        ('late', _('Late')),
        ('absent', _('Absent')),
        ('excused', _('Excused')),
    ]
    session = models.ForeignKey(AttendanceSession, on_delete=models.CASCADE, related_name='records')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attendance_records')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='present')
    check_in_time = models.DateTimeField(auto_now_add=True)
    notes = models.CharField(max_length=300, blank=True)

    class Meta:
        unique_together = ('session', 'user')
        ordering = ['-check_in_time']

    def __str__(self):
        return f"{self.user} → {self.session} ({self.status})"
