from django.core.mail import get_connection, EmailMultiAlternatives
from django.conf import settings
from celery import shared_task


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 5, "countdown": 30},
    retry_backoff=True,
    retry_jitter=True,
    acks_late=True,
)
def send_email_task(self, payload):
    connection = get_connection()

    # --- ЗАХИСТ ВІД TYPE ERROR ---
    recipients = payload["to"]

    # Якщо прийшов рядок (один email), загортаємо її в список
    if isinstance(recipients, str):
        recipients = [recipients]
    # Якщо прийшло щось інше, що не є ітератором (наприклад, None), робимо порожній список
    elif not isinstance(recipients, (list, tuple)):
        recipients = list(recipients) if recipients else []
    # ---------------------------------

    message = EmailMultiAlternatives(
        subject=payload["subject"],
        body=payload["body"],
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=recipients,
        connection=connection,
    )

    if payload.get("html"):
        message.attach_alternative(payload["html"], "text/html")

    message.send(fail_silently=False) # For logging in Celery