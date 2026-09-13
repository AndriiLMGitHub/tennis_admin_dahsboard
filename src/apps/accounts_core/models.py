from django.conf.urls.static import static
from django.contrib.auth.models import AbstractUser
from django.db import models

from .managers import UserManager
from django.utils.translation import gettext_lazy as _

from .utils import _user_avatar_upload_path
from .validators import validate_avatar_size


class User(AbstractUser):
    ROLE_CHOICES = (
        ('Coach', 'Coach'),
        ('Student', 'Student'),
        ('Nutrition', 'Nutrition'),
        ('Psychology', 'Psychology'),
    )

    USER_STATUS = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    id: int
    username = None
    email = models.EmailField(_("Email address"), unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, null=True, blank=True)
    user_status = models.CharField(max_length=20, choices=USER_STATUS, null=True, blank=True)

    telegram_chat_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text=_("The trainer's personal Telegram channel for receiving client files.")
    )

    # Extra Fields
    avatar = models.FileField(
        upload_to=_user_avatar_upload_path,
        validators=[validate_avatar_size],
        blank=True,
        null=True,
        help_text=_("Upload your avatar to this personal dashboard.")
    )
    country = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text=_("Select your country of residence to adapt timezones and regional settings.")
    )
    currency = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text=_("Choose the primary currency for displaying prices and processing payments.")
    )
    language = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text=_("Choose your language")
    )
    company = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text=_("Choose your company")
    )
    company_site = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text=_("Choose your company site")
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text=_("Choose your phone number")
    )
    timezone = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text=_("Choose your timezone")
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    @property
    def avatar_color_class(self):
        # Розширена палітра: 6 стандартних Metronic + 4 наших кастомних
        colors = [
            'primary', 'success', 'info', 'warning', 'danger', 'dark',
            'purple', 'teal', 'pink', 'indigo'
        ]

        if not self.id:
            return 'primary'

        index = self.id % len(colors)
        return colors[index]

    @property
    def is_approved_coach(self):
        return self.role == "Coach" and self.user_status == "approved"

    @property
    def avatar_url(self):
        """
        Повертає URL файлу з хмари (R2).
        Якщо файлу немає, повертає None. Логіка заглушок делегується шаблонам.
        """
        if self.avatar and self.avatar.name:
            try:
                return self.avatar.url
            except Exception:
                pass
        return None


    def __str__(self):
        return self.email


