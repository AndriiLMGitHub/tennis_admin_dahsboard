import os
import uuid

from django.contrib.auth.base_user import AbstractBaseUser
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.http import QueryDict
from django.utils.datastructures import MultiValueDict
from django.utils.translation import gettext_lazy as _

from django.conf import settings

_PROFILE_TEXT_FIELDS = ("first_name", "last_name", "country", "language", "currency")

def _validate_avatar(avatar: InMemoryUploadedFile) -> None:
    max_size_mb = 50
    allowed_types = {"image/jpeg", "image/png", "image/webp"}

    if avatar.size > max_size_mb * 1024 * 1024:
        raise ValidationError(_("Avatar file size must not exceed %(max)s MB.") % {"max": max_size_mb})

    if avatar.content_type not in allowed_types:
        raise ValidationError(_("Unsupported image format. Use JPEG, PNG or WebP."))


def _apply_profile_updates(
    user: AbstractBaseUser,
    post: QueryDict,
    files: MultiValueDict,
) -> list[str]:
    updated: list[str] = []

    for field in _PROFILE_TEXT_FIELDS:
        value = post.get(field, "").strip()
        if getattr(user, field) != value:
            setattr(user, field, value)
            updated.append(field)

    if avatar := files.get("avatar"):
        _validate_avatar(avatar)
        user.avatar = avatar
        updated.append("avatar")

    return updated


def _user_avatar_upload_path(instance, filename):
    """
    Генерує унікальний шлях для аватара.
    Формат: avatars/user_ID_hash.jpg
    """
    unique_hash = uuid.uuid4().hex[:8]
    # Примусово зберігаємо як .jpg для стандартизації
    return f"{settings.UPLOAD_DIRECTORIES['avatars']}/user_{instance.pk}_{unique_hash}.jpg"