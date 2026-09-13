from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model

User = get_user_model()


class Feedback(models.Model):
    # 1. Зв'язок із користувачем платформи (опціонально, якщо пишуть гості)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="feedbacks",
        null=True,
        blank=True,
        verbose_name=_("User")
    )

    # Залишаємо ці поля як фолбек, якщо форму заповнить неавторизований гість.
    # Якщо користувач авторизований — у в'юсі автоматично підтягнемо дані з request.user
    name = models.CharField(max_length=255, blank=True, verbose_name=_("Name"))
    email = models.EmailField(verbose_name=_("Email"))


    subject = models.CharField(max_length=255, verbose_name=_("Subject"))
    message = models.TextField(verbose_name=_("Message"))

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated at"))

    class Meta:
        verbose_name = _("Feedback")
        verbose_name_plural = _("Feedback Emails")
        ordering = ['-created_at']
        # Індекси для швидкої фільтрації в адмінці за статусом та датою
        indexes = [
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"#{self.id} | {self.subject}"

    @property
    def comment(self):
        """
        Аліас для сумісності з версткою.
        Оскільки у верстці використовується `request_item.comment`,
        цей проперті дозволить шаблону безболісно читати поле `message`.
        """
        return self.message

    @property
    def get_specialty_needed_display(self):
        """Аліас сумісності для виведення теми в один інтерфейс."""
        return self.subject


class FAQCategory(models.Model):
    """
    Категорії для групування FAQ (наприклад: "Оплата", "Тренування", "Техпідтримка").
    """
    title = models.CharField(max_length=255, verbose_name=_("Category Title"))
    slug = models.SlugField(max_length=255, unique=True, db_index=True, verbose_name=_("Slug"))
    sort_order = models.PositiveIntegerField(default=0, db_index=True, verbose_name=_("Sort Order"))
    is_active = models.BooleanField(default=True, db_index=True, verbose_name=_("Is Active"))

    class Meta:
        ordering = ('sort_order', 'title')
        verbose_name = _("FAQ Category")
        verbose_name_plural = _("FAQ Categories")

    def __str__(self):
        return self.title


class FAQItem(models.Model):
    """
    Конкретні запитання та відповіді, прив'язані до категорій.
    """
    category = models.ForeignKey(
        FAQCategory,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_("Category")
    )
    question = models.TextField(verbose_name=_("Question"))
    answer = models.TextField(verbose_name=_("Answer"))  # Можна використовувати HTML (для Metronic)

    # Керування відображенням та сортуванням
    sort_order = models.PositiveIntegerField(default=0, db_index=True, verbose_name=_("Sort Order"))
    is_published = models.BooleanField(default=True, db_index=True, verbose_name=_("Is Published"))

    # Логування змін
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', '-created_at']
        verbose_name = _("FAQ Item")
        verbose_name_plural = _("FAQ Items")

    def __str__(self):
        # Повертаємо перші 50 символів питання для відображення в адмінці
        return self.question[:50] if len(self.question) <= 50 else f"{self.question[:50]}..."