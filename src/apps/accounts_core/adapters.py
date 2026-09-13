# adapters.py
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.urls import reverse
from allauth.account.models import EmailAddress

class MySocialAccountAdapter(DefaultSocialAccountAdapter):

    def save_user(self, request, sociallogin, form=None):
        """
        Використовуємо super().save_user, щоб socialaccount записався в DB.
        Потім встановлюємо role і user_status.
        Також позбуваємось confirm-email для Google.
        """
        # 1 викликаємо базовий save_user
        user = super().save_user(request, sociallogin, form)

        # 2 role/coach_status
        if not user.role:
            user.role = None  # або 'User', якщо хочеш
            user.user_status = None
            user.save()

        # 3 позбавляємось confirm-email
        email_obj, created = EmailAddress.objects.get_or_create(user=user, email=user.email)
        email_obj.verified = True
        email_obj.primary = True
        email_obj.save()

        return user

    def get_login_redirect_url(self, request):
        # якщо роль не задана → редіректимо на select-role
        if not request.user.role:
            return reverse("select_role")
        return super().get_login_redirect_url(request)