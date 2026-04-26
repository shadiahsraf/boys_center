from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns
from django.views.generic import RedirectView
from users.views import DashboardView, CustomLoginView, LandingView
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
    path('admin/', admin.site.urls),
    path('attendance/api/', include('attendance.api_urls')),
    # Root: redirect to localized version
    path('', RedirectView.as_view(url='/en/', permanent=False)),
]

urlpatterns += i18n_patterns(
    # Public landing page at site root
    path('', LandingView.as_view(), name='landing'),
    path('auth/login/', CustomLoginView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(next_page='/en/'), name='logout'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('users/', include('users.urls', namespace='users')),
    path('attendance/', include('attendance.urls', namespace='attendance')),
    path('evaluations/', include('evaluations.urls', namespace='evaluations')),
    path('sports/', include('sports.urls', namespace='sports')),
    path('events/', include('events.urls', namespace='events')),
    path('news/', include('news.urls', namespace='news')),
    path('reports/', include('reports.urls', namespace='reports')),
    prefix_default_language=True,
)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
