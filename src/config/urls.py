from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import include, path, reverse_lazy
from django.views.generic import RedirectView, TemplateView


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/dashboard_base.html"
    login_url = reverse_lazy("account_login")


account_urlpatterns = [
    path("", include("allauth.urls")),
    path("core/", include("apps.accounts_core.urls")),
]

dashboard_urlpatterns = [
    path("", DashboardView.as_view(), name="index"),
    path("consulting/", include("apps.consulting.urls")),
    path("feedback/", include("apps.feedback.urls")),
]

localized_urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include(account_urlpatterns)),
    path("dashboard/", include(dashboard_urlpatterns)),
    path("", RedirectView.as_view(pattern_name="index"), name="root-redirect"),
]


# ─── Non-localized routes (API, webhooks, language switching) ────────────────
urlpatterns = [
    path("i18n/", include("django.conf.urls.i18n")),
]

# ─── Localized routes ─────────────────────────────────────────────────────────
urlpatterns += i18n_patterns(*localized_urlpatterns)
