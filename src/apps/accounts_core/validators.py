from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from config import settings


def validate_avatar_size(file):
    """
    Validator to limit the size of the uploaded avatar to MAX_UPLOAD_SIZE AVATAR MB.
    """
    max_size_mb = settings.MAX_UPLOAD_SIZE_AVATAR
    limit = max_size_mb * 1024 * 1024


    if file.size > limit:
        raise ValidationError(
            _("File size extends maximum limit of %(max_size)s MB."),
            params={'max_size': max_size_mb},
        )