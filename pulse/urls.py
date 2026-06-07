from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from pulse.favicon import favicon_svg

urlpatterns = [
    path('static/favicon.svg', favicon_svg, name='favicon_svg'),
    path('favicon.ico', favicon_svg),
    path('admin/', admin.site.urls),
    path('accounts/', include('users.urls')),
    path('plans/', include('plans.urls')),
    path('', include('dashboard.urls')),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
