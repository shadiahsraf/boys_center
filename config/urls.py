from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns
from django.http import HttpResponse, FileResponse
from django.views.decorators.cache import never_cache
from django.views.generic import RedirectView
from users.views import DashboardView, CustomLoginView, LandingView
from django.contrib.auth.views import LogoutView


# ─── PWA service-worker view ────────────────────────────────────────────────
# Served from the site root so its scope can cover the whole app. We add the
# explicit Service-Worker-Allowed header so the browser permits scope: '/'.
@never_cache
def service_worker(request):
    sw_path = settings.BASE_DIR / 'static' / 'pwa' / 'sw.js'
    response = FileResponse(open(sw_path, 'rb'),
                            content_type='application/javascript')
    response['Service-Worker-Allowed'] = '/'
    response['Cache-Control'] = 'no-cache'
    return response


def manifest_view(request):
    """Serve manifest from root — some browsers prefer it there."""
    mf = settings.BASE_DIR / 'static' / 'pwa' / 'manifest.webmanifest'
    return FileResponse(open(mf, 'rb'),
                        content_type='application/manifest+json')

urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
    path('admin/', admin.site.urls),
    path('attendance/api/', include('attendance.api_urls')),
    # PWA — served from root so the service-worker scope can cover the whole site
    path('sw.js', service_worker, name='service_worker'),
    path('manifest.webmanifest', manifest_view, name='manifest'),
    # Root: redirect to Arabic-first version
    path('', RedirectView.as_view(url='/ar/', permanent=False)),
]

urlpatterns += i18n_patterns(
    # Public landing page at site root
    path('', LandingView.as_view(), name='landing'),
    path('auth/login/', CustomLoginView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(next_page='/ar/'), name='logout'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('users/', include('users.urls', namespace='users')),
    path('attendance/', include('attendance.urls', namespace='attendance')),
    path('evaluations/', include('evaluations.urls', namespace='evaluations')),
    path('sports/', include('sports.urls', namespace='sports')),
    path('events/', include('events.urls', namespace='events')),
    path('news/', include('news.urls', namespace='news')),
    path('reports/', include('reports.urls', namespace='reports')),
    path('notifications/', include('notifications.urls', namespace='notifications')),
    path('quiz/', include('quiz.urls', namespace='quiz')),
    path('challenge/', include('dailychallenge.urls', namespace='dailychallenge')),
    path('rate/', include('ratings.urls', namespace='ratings')),
    prefix_default_language=True,
)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
