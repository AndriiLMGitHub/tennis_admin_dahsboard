from django.conf import settings
from django.template.loader import render_to_string
from infrastructure.email.tasks import send_email_task


def send_feedback_notification(feedback_instance):
    """
    Формує payload та відправляє задачу в Celery для сповіщення підтримки.
    """
    support_email = getattr(settings, 'SUPPORT_EMAIL', settings.DEFAULT_FROM_EMAIL)

    # Контекст для рендерингу шаблонів
    context = {'feedback': feedback_instance}

    # Рендеримо тіло листа з шаблону
    text_body = render_to_string('feedback/emails/notification.txt', context)

    # Якщо колись захочеш додати HTML:
    # html_body = render_to_string('feedback/emails/notification.html', context)
    html_body = None

    payload = {
        "subject": f"New Contact Request: {feedback_instance.subject}",
        "body": text_body,
        "to": [support_email],
        "html": html_body
    }

    # Делегуємо виконання брокеру (Redis)
    send_email_task.delay(payload)