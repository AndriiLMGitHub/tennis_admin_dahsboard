from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AccountsCoreConfig(AppConfig):
    name = "apps.accounts_core"
    label = "accounts_core"

    verbose_name = _("Accounts Core")
