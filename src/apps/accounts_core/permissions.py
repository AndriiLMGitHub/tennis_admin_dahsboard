from functools import wraps

from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect


def coach_only(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        user = request.user

        # 1. Перевірка авторизації
        if not user.is_authenticated:
            return redirect('account_login')

        # 2. Перевірка ролі (викидаємо 403, бо це питання прав)
        if user.role != "Coach":
            raise PermissionDenied

        # 3. Перевірка статусу (редірект, бо це логічний стан account)
        if user.coach_status != "approved":
            return redirect("coach_pending_page")

        return view_func(request, *args, **kwargs)

    return _wrapped_view


def superuser_only(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        # Замість редіректу викидаємо стандартне вікно 403
        raise PermissionDenied
    return _wrapped_view