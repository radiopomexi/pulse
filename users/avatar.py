from __future__ import annotations

from django.core.files.uploadedfile import UploadedFile


def apply_avatar_change(user, uploaded_file: UploadedFile | None = None, *, clear: bool = False) -> None:
    if uploaded_file:
        user.avatar_data = uploaded_file.read()
        user.avatar_content_type = uploaded_file.content_type or 'image/jpeg'
        _clear_legacy_avatar_file(user)
        return
    if clear:
        user.avatar_data = None
        user.avatar_content_type = ''
        _clear_legacy_avatar_file(user)


def _clear_legacy_avatar_file(user) -> None:
    if not user.avatar:
        return
    try:
        user.avatar.delete(save=False)
    except OSError:
        pass
    user.avatar = None
