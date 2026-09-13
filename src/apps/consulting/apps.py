from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ConsultingConfig(AppConfig):
    name = "apps.consulting"

    verbose_name = _("Consulting")