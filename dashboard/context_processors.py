from __future__ import annotations

from typing import Any

from django.utils import timezone
from django.utils.timesince import timesince


def notifications(request) -> dict[str, Any]:
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return {'pulse_notifications': {'unread_count': 0, 'items': []}}
    from .models import Notification

    user = request.user
    unread_count = Notification.objects.filter(recipient=user, is_read=False).count()
    items: list[dict[str, Any]] = []
    now = timezone.now()
    for n in Notification.objects.filter(recipient=user).order_by('-created_at')[:20]:
        items.append({'id': n.pk, 'message': n.message, 'link': n.link or '', 'is_read': n.is_read, 'created_at': n.created_at, 'time_label': timesince(n.created_at, now) + ' назад'})
    return {'pulse_notifications': {'unread_count': unread_count, 'items': items}}
