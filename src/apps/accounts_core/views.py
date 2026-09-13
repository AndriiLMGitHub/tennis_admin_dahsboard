from allauth.account.forms import ChangePasswordForm
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, get_backends, update_session_auth_hash, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST
from requests import Request

from apps.accounts_core.constants import LANGUAGES_DATA, TIMEZONES_DATA, COUNTRIES_DATA, CURRENCIES_DATA
from apps.accounts_core.forms import RoleForm, CustomSignupForm, StudentProfileUpdateForm, CoachProfileUpdateForm
from apps.accounts_core.models import User
from apps.consulting.decorators import student_required, coach_required
from infrastructure.email.tasks import send_email_task
from django.utils.translation import gettext_lazy as _


# ==========================================
# AUTH SYSTEM VIEWS (WITH ROLES)
# ==========================================

@login_required
def select_role(request: Request):
    user = request.user

    if user.is_superuser or user.is_staff:
        return redirect("admin:index")

    # Якщо роль вже обрана — відправляємо на головну
    if user.role:
        return redirect("index")

    form = RoleForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        role_choice = form.cleaned_data["role"]
        user.role = role_choice

        if role_choice in ["Coach", "Psychology", "Nutrition"]:
            user.user_status = "pending"

            for recipient, body_text in [
                (user.email, _(f"You have successfully registered as a {user.role}.")),
                (settings.DEFAULT_FROM_EMAIL, f"New user registration pending: {user.email}"),
            ]:
                if recipient:
                    payload = {
                        "subject": f"{user.role} Registration Pending",
                        "body": body_text,
                        "html": f"<p>{body_text}</p>",
                        "to": [recipient],
                    }
                    send_email_task.delay(payload)
        else:
            user.user_status = None

        user.save()

        if not hasattr(user, "backend"):
            backends = get_backends()
            if backends:
                backend = backends[0]
                user.backend = f"{backend.__module__}.{backend.__class__.__name__}"

        login(request, user)
        return redirect("index")

    return render(request, "account/select_role.html", {"form": form})


def register_coach_view(request):
    form = CustomSignupForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        # Тепер форма сама відправить листи і користувачу, і адміну всередині методу .save()
        form.save(request)
        return redirect("account_login")

    return render(request, "account/sign_up_coach.html", {
        "form": form,
        "is_coach": True
    })


# ==========================================
# PROFILE STUDENT VIEWS
# ==========================================

@login_required
def profile_router_view(request):
    """
    Універсальний роутер профілю.
    Бере на себе логіку визначення, куди саме відправити поточного користувача.
    """
    user_role = request.user.role

    if user_role == 'Student':
        return redirect('student_profile')  # Перекидає на URL студента
    elif user_role == 'Coach':
        return redirect('coach_profile')  # Перекидає на URL тренера
    elif request.user.is_superuser:
        return redirect('admin:index')  # Перекидає на головного адміна
    elif user_role == 'Psychology':
        return redirect('psychology')  # Перекидає на URL психолога
    elif user_role == 'Nutrition':
        return redirect('nutrition_dashboard')  # Перекидає на URL нутриціолога
    else:
        # Якщо роль не визначена або це суперадмін - кидаємо на стандартну адмінку або 404
        raise Http404("Profile not found for this role.")


@student_required
def student_profile_view(request):
    return render(request, "dashboard/student/profile/view.html")


@student_required
def student_profile_edit_view(request):
    """
    Професійне оновлення профілю студента через ModelForm.
    """
    user = request.user

    if request.method == "POST":
        # Зв'язуємо форму з даними з POST-запиту, файлами та поточним користувачем
        form = StudentProfileUpdateForm(request.POST, request.FILES, instance=user)

        if form.is_valid():
            form.save()
            messages.success(request, _("You have successfully updated your profile."))
            return redirect("student_profile_edit")  # Замініть на актуальний name вашого url
        else:
            messages.error(request, _("Please correct the errors below."))
    else:
        # GET-запит: створюємо форму, заповнену поточними даними користувача
        form = StudentProfileUpdateForm(instance=user)

    context = {
        "form": form,
        "countries": COUNTRIES_DATA,
        "languages": LANGUAGES_DATA,
        "timezones": TIMEZONES_DATA,
        "currencies": CURRENCIES_DATA,
    }

    return render(request, "dashboard/student/profile/edit.html", context)


# ==========================================
# PROFILE COACH VIEWS
# ==========================================

@coach_required
def coach_profile_view(request):
    return render(request, "dashboard/coach/profile/view.html", {})


@coach_required
def coach_profile_edit_view(request):
    """
        Професійне оновлення профілю студента через ModelForm.
        """
    user = request.user

    if request.method == "POST":
        # Зв'язуємо форму з даними з POST-запиту, файлами та поточним користувачем
        form = CoachProfileUpdateForm(request.POST, request.FILES, instance=user)

        if form.is_valid():
            form.save()
            messages.success(request, _("You have successfully updated your profile."))
            return redirect("coach_profile_edit")
        else:
            messages.error(request, _("Please correct the errors below."))
    else:
        # GET-запит: створюємо форму, заповнену поточними даними користувача
        form = StudentProfileUpdateForm(instance=user)

    context = {
        "form": form,
        "countries": COUNTRIES_DATA,
        "languages": LANGUAGES_DATA,
        "timezones": TIMEZONES_DATA,
        "currencies": CURRENCIES_DATA,
    }

    return render(request, "dashboard/coach/profile/edit.html", context)


# ==========================================
# PROFILE COMMON VIEWS
# ==========================================

@require_POST
@login_required
def deactivate_account_view(request, expected_role=None):
    """
    Універсальний контролер деактивації акаунта з перевіркою згоди.
    Гарантує повний DRY, перевірку checkbox та сувору рольову ізоляцію.
    """
    user = request.user

    # 1. СУВОРИЙ ЗАХИСТ РОЛЕЙ: Блокуємо доступ, якщо роль не збігається з очікуваною.
    # (Регістр має строго відповідати базі даних: 'Student' або 'Coach')
    if expected_role and user.role != expected_role:
        raise PermissionDenied(_("You do not have permission to deactivate an account on this endpoint."))

    # 2. Перевірка згоди (захист від випадкового надсилання форми)
    if request.POST.get('confirm_deactivation') == 'on':

        # SOFT DELETE: Забираємо доступ, але зберігаємо об'єкт у базі
        user.is_active = False
        user.save()

        # Знищення сесії (КРИТИЧНО)
        logout(request)

        messages.success(request, _("Your account has been successfully deactivated."))
        return redirect('account_login')  # Стандартний URL для Allauth

    else:
        messages.error(request, _("You must check the box to confirm deactivation."))

        if user.role == 'Coach':
            return redirect('coach_profile')
        return redirect('student_profile')


@login_required
def common_profile_security_view(request, expected_role=None, template_name=None, redirect_url_name=None):
    """
    Універсальний контролер налаштувань безпеки (зміна пароля тощо).
    Повністю абстрагований від конкретних ролей та HTML-шаблонів.
    """
    user = request.user

    if expected_role and user.role != expected_role:
        raise PermissionDenied(_("You do not have permission to access this security endpoint."))

    password_form = ChangePasswordForm(user=user)

    if request.method == "POST":
        if 'action_change_password' in request.POST:
            if request.user.socialaccount_set.exists():
                raise PermissionDenied(
                    _("Users authenticated via social networks are not allowed to change local passwords."))
            password_form = ChangePasswordForm(data=request.POST, user=user)

            if password_form.is_valid():
                password_form.save()

                update_session_auth_hash(request, password_form.user)

                messages.success(request, _("Your password has been successfully updated."))
                return redirect(redirect_url_name)
            else:
                messages.error(request, _("Please correct the errors in the password form."))

    context = {
        'password_form': password_form,
        'role': expected_role,
    }

    return render(request, template_name, context)
