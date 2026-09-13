from django.shortcuts import redirect
from django.urls import reverse, NoReverseMatch
import logging

logger = logging.getLogger(__name__)


class CheckRoleMiddleware:
    """
    Blocking Middleware. If the user is authorized, is not an admin
    and has not selected a role (role is None or empty) -> forced redirect to select-role.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user

        # 1. Якщо користувач не авторизований — Middleware взагалі не втручається
        if not user.is_authenticated:
            return self.get_response(request)

        # 2. БЕЗПЕКА АДМІНІСТРАТОРА: Superusers та персонал повністю ігнорують цей Middleware
        if user.is_superuser or user.is_staff or user.role == "Admin":
            return self.get_response(request)

        # 3. БІЛИЙ СПИСОК URL (Ці маршрути доступні користувачу БЕЗ ролі)
        path = request.path

        # Ігноруємо адмінку, статику, медіа та системні запитиToolbar (якщо є debug_toolbar)
        if (
                path.startswith('/admin/') or
                path.startswith('/static/') or
                path.startswith('/media/') or
                path.startswith('/__debug__/')
        ):
            return self.get_response(request)

        # Динамічно отримуємо URL сторінки вибору ролі (з урахуванням i18n/локалізації)
        try:
            select_role_url = reverse("select_role")
            logout_url = reverse("account_logout")  # Дозволяємо log out, якщо user застряг
        except NoReverseMatch:
            # Якщо urls ще не зареєстровані (наприклад, під час міграцій) — пропускаємо
            return self.get_response(request)

        # Ігноруємо саму сторінку вибору ролі та сторінку виходу з account
        if path.startswith(select_role_url) or path.startswith(logout_url):
            return self.get_response(request)

        # 4. ФІЛЬТРАЦІЯ ТА РЕДІРЕКТ
        # Якщо ролі немає (None або порожній рядок) — примусово відправляємо обирати роль
        if not user.role:
            logger.warning(f"User {user.email} missing role. Redirecting to select_role.")
            return redirect("select_role")

        return self.get_response(request)
