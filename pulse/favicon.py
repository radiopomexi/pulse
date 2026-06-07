"""Отдача favicon без зависимости от staticfiles в dev/ASGI."""
from django.conf import settings
from django.http import FileResponse, Http404


def favicon_svg(request):
    path = settings.BASE_DIR / 'static' / 'favicon.svg'
    if not path.is_file():
        raise Http404()
    resp = FileResponse(path.open('rb'), content_type='image/svg+xml')
    resp['Cache-Control'] = 'public, max-age=86400'
    return resp
