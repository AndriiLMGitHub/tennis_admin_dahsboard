import logging
from django.db import transaction
from infrastructure.email.tasks import send_email_task
from .utils import prepare_request_email_payload
from .models import RequestStatusHistory

logger = logging.getLogger(__name__)


def assign_coach_to_request(request_obj, new_coach, assigned_by_user, base_url):
    """Призначає коуча та ініціює відправку email-у."""
    request_obj.assigned_specialist = new_coach
    request_obj.save(update_fields=['assigned_specialist'])

    logger.info(f"Coach {new_coach.email} assigned to Request {request_obj.id}")

    coach_emails = [new_coach.email]
    payload = prepare_request_email_payload(
        request_obj=request_obj,
        recipient_emails=coach_emails,  # Сюди йде список пошт
        base_url=base_url,  # Сюди йде домен
        recipient_role='coach'  # Передаємо роль коуча для адаптації Metronic-шаблону
    )

    transaction.on_commit(lambda: send_email_task.delay(payload))


def log_status_change(request_obj, old_status, new_status, changed_by_user):
    """Фіксує зміну статусу в історії."""
    RequestStatusHistory.objects.create(
        request=request_obj,
        old_status=old_status,
        new_status=new_status,
        changed_by=changed_by_user
    )
    logger.info(f"Request {request_obj.id} status changed from {old_status} to {new_status}")