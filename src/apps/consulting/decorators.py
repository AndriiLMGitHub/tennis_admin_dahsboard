from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from functools import wraps
from django.utils.translation import gettext_lazy as _

from django.shortcuts import redirect


def student_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())

        # If the user is not authorized or not a student, we throw a 403 Forbidden
        if request.user.role != "Student":
            raise PermissionDenied(_("You do not have permission to access the Student dashboard."))

        return view_func(request, *args, **kwargs)

    return _wrapped_view


def coach_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())

        # If the user is not authorized or not a coach, we throw a 403 Forbidden
        if request.user.role != "Coach":
            raise PermissionDenied(_("You do not have permission to access the Coach dashboard."))
        return view_func(request, *args, **kwargs)

    return _wrapped_view


def superuser_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.is_superuser:
            return view_func(request, *args, **kwargs)

        raise PermissionDenied(_("You do not have permission to access the Admin dashboard."))

    return _wrapped_view


def psychology_required(view_func):
    """
    Декоратор для перевірки ролі Психолога.
    Примусово блокує доступ (403 Forbidden), якщо роль користувача не 'Psychology'.
    """

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.shortcuts import redirect
            return redirect('account_login')

        if request.user.role != 'Psychology':
            raise PermissionDenied(_("You do not have permission to access the Psychology dashboard."))

        return view_func(request, *args, **kwargs)

    return _wrapped_view


def nutrition_required(view_func):
    """
    Декоратор для перевірки ролі Нутриціолога (Nutrition).
    Примусово блокує доступ (403 Forbidden), якщо роль користувача не 'Nutrition'.
    """

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # 1. Перевірка авторизації
        if not request.user.is_authenticated:
            return redirect('account_login')

        # 2. Суворий захист домену ролі
        if request.user.role != 'Nutrition':
            raise PermissionDenied(_("You do not have permission to access the Nutrition dashboard."))

        return view_func(request, *args, **kwargs)

    return _wrapped_view


def allowed_roles_only(allowed_roles):
    """
    Декоратор доступу для конкретних ролей.
    Superusers та персонал (is_staff/is_superuser) отримують відмову (або redirect).
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # 1. Перевірка авторизації
            if not request.user.is_authenticated:
                return redirect('account_login')

            # 2. Жорсткий блок для суперкористувачів та персоналу
            if request.user.is_superuser or request.user.is_staff or request.user.role == "Admin":
                # Варіант А: Викидає 403 Forbidden (найбільш правильний REST-підхід)
                raise PermissionDenied(_("You do not have permission to access the Admin dashboard."))

                # Варіант Б: Якщо хочеш замість помилки просто викидати його в адмінку, розкоментуй:
                # return redirect('admin:index')

            # 3. Перевірка дозволених ролей (Student або Coach)
            if request.user.role in allowed_roles:
                return view_func(request, *args, **kwargs)

            # Якщо роль інша (наприклад, якась нова роль), теж викидаємо 403
            raise PermissionDenied

        return _wrapped_view

    return decorator
