from allauth.account.forms import SignupForm, LoginForm, ResetPasswordForm, ResetPasswordKeyForm
from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from infrastructure.email.tasks import send_email_task


User = get_user_model()

ROLE_CHOICES = (
    ('Coach', _('Coach')),
    ('Student', _('Student')),
    ('Psychology', _('Psychology')),
    ('Nutrition', _('Nutrition')),
)


class RoleForm(forms.Form):
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        label=_("Role")
    )


class CustomSignupForm(SignupForm):
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        widget=forms.Select(attrs={
            "class": "form-select bg-transparent",
        }),
        required=True
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["email"].widget = forms.EmailInput(attrs={
            "class": "form-control bg-transparent",
            "placeholder": "Email",
            "autocomplete": "off",
        })

        self.fields["password1"].widget.attrs.update({
            "class": "form-control bg-transparent",
            "placeholder": "Password",
        })

        self.fields["password2"].widget.attrs.update({
            "class": "form-control bg-transparent",
            "placeholder": "Repeat password",
        })

        self.fields["email"].error_messages["required"] = _("Enter correct email.")
        self.fields["password1"].error_messages["required"] = _("Enter correct password.")
        self.fields["password2"].error_messages["required"] = _("Enter correct password repeat")

    def save(self, request):
        # Спочатку виконуємо базове збереження allauth
        user = super().save(request)
        role_choice = self.cleaned_data.get("role", "Student")
        user.role = role_choice

        # 🚨 ОПТИМІЗАЦІЯ: Чиста перевірка через список (замість chained 'or')
        if role_choice in ["Coach", "Psychology", "Nutrition"]:
            user.user_status = "pending"

            # 🚨 ВІДПРАВКА ЛИСТІВ ТЕПЕР ПРАЦЮЄ І ПРИ ПРЯМІЙ РЕЄСТРАЦІЇ
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
        return user


class CustomLoginForm(LoginForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["login"].widget = forms.EmailInput(attrs={
            "class": "form-control bg-transparent",
            "placeholder": "Email address",
            "autocomplete": "off",
        })

        self.fields["password"].widget = forms.PasswordInput(attrs={
            "class": "form-control bg-transparent",
            "placeholder": "Password",
            "autocomplete": "off",
        })

        self.fields["login"].error_messages["required"] = _("Enter correct email.")
        self.fields["password"].error_messages["required"] = _("Enter correct password.")


class CustomResetPasswordForm(ResetPasswordForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].widget = forms.EmailInput(attrs={
            "class": "form-control bg-transparent",
            "placeholder": _("Email"),
            "autocomplete": "off",
        })

        self.fields["email"].error_messages["required"] = _("Enter correct email.")


class CustomResetPasswordFromKeyForm(ResetPasswordKeyForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["password1"].widget.attrs.update({
            "class": "form-control bg-transparent",
            "placeholder": "New Password",
            "autocomplete": "new-password",
        })

        self.fields["password2"].widget.attrs.update({
            "class": "form-control bg-transparent",
            "placeholder": "Confirm Password",
            "autocomplete": "new-password",
        })


        for name in ("password1", "password2"):
            field = self.fields[name]
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = (existing + " form-control bg-transparent").strip()


class StudentProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            'avatar',
            'first_name',
            'last_name',
            'phone_number',
            'timezone',
            'country',
            'language',
            'currency'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Робимо критичні поля обов'язковими для заповнення
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['timezone'].required = True
        self.fields['language'].required = True

    def clean(self):
        cleaned_data = super().clean()

        # Перехоплюємо прихований прапорець від Metronic
        # 'avatar_remove' дорівнює '1', якщо користувач натиснув іконку видалення
        avatar_remove_flag = self.data.get('avatar_remove')

        if avatar_remove_flag == '1':
            # Очищаємо поле аватара.
            # Після збереження форми django-cleanup сам видалить файл із R2.
            cleaned_data['avatar'] = None
            self.instance.avatar = None

        return cleaned_data


class CoachProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            'avatar',
            'first_name',
            'last_name',
            'phone_number',
            'timezone',
            'country',
            'language',
            'currency'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Робимо критичні поля обов'язковими для заповнення
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['timezone'].required = True
        self.fields['language'].required = True

    def clean(self):
        cleaned_data = super().clean()

        # Перехоплюємо прихований прапорець від Metronic
        # 'avatar_remove' дорівнює '1', якщо користувач натиснув іконку видалення
        avatar_remove_flag = self.data.get('avatar_remove')

        if avatar_remove_flag == '1':
            # Очищаємо поле аватара.
            # Після збереження форми django-cleanup сам видалить файл із R2.
            cleaned_data['avatar'] = None
            self.instance.avatar = None

        return cleaned_data