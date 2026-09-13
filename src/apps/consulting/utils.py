from datetime import datetime
import logging
from typing import Dict, Any

from django.core.files.storage import default_storage
from django.template.exceptions import TemplateDoesNotExist
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

# Logger init
logger = logging.getLogger(__name__)


def force_delete_from_r2(file_path: str) -> bool:
    """
    Directly delete an object from Cloudflare R2 (or other S3-compatible storage).

    The function checks for the existence of the file, performs the deletion, and verifies
    the result. Any network errors or permissions issues are caught
    and logged.

    Args:
    file_path (str): Relative path to the file in the storage.
    Example: 'requests/materials/Document1_E0H0MBO.doc'.

    Returns:
    bool: True if the file was successfully deleted.
    False if the file was not found, was not deleted due to insufficient permissions,
    or there was an error connecting to the storage.
    """
    if not file_path:
        logger.warning("force_delete_from_r2 called with an empty file_path.")
        return False

    try:
        # 1. ПЕРЕВІРКА: Чи існує файл фізично?
        if default_storage.exists(file_path):
            # 2. ВИДАЛЕННЯ: Відправляє команду DELETE в Cloudflare
            default_storage.delete(file_path)

            # 3. ВЕРИФІКАЦІЯ: Перевіряємо, чи зник об'єкт
            if not default_storage.exists(file_path):
                logger.info(f"SUCCESS: File '{file_path}' deleted from R2.")
                return True
            else:
                logger.error(
                    f"FAILURE: File '{file_path}' still exists after delete attempt. Check R2 IAM permissions/bucket policies.")
                return False
        else:
            logger.info(f"NOT FOUND: File '{file_path}' doesn't exist in R2 storage. Nothing to delete.")
            return False

    except Exception as e:
        # Перехоплюємо botocore.exceptions.ClientError, urllib3.exceptions тощо
        logger.exception(
            f"CRITICAL ERROR: Failed to communicate with R2 while deleting '{file_path}'. Details: {str(e)}")
        return False


def prepare_request_email_payload(
        request_obj,
        recipient_emails,
        base_url,
        recipient_role='admin'
) -> Dict[str, Any]:
    """
    Universal payload builder for letters.
    recipient_role: 'admin' or 'coach'
    """
    specialty_display = request_obj.get_specialty_needed_display()
    if recipient_role == 'admin':
        subject = f"🚨 New platform request: {specialty_display}"
    else:
        subject = f"🎾 New assignment: {specialty_display}"

    # Базовий URL сайту (можна зашити в settings або брати з Site)
    # Для локальної розробки: http://127.0.0.1:8000
    base_url = "http://127.0.0.1:8000"

    context = {
        "user_email": request_obj.user.email,
        "comment": request_obj.comment,
        "specialty": specialty_display,
        "recipient_role": recipient_role,
        "admin_url": f"{base_url}{reverse('admin:consulting_request_change', args=[request_obj.id])}",
        "dashboard_url": f"{base_url}{reverse('index')}",
    }

    try:
        body_html = render_to_string("feedback/emails/request_notification.html", context)
    except TemplateDoesNotExist:
        logger.error("Template 'feedback/emails/request_notification.html' not found! Using fallback.")
        body_html = f"Request #{request_obj.id}. Client: {request_obj.user.email}. Comment: {request_obj.comment}"

    # Text fallback (required for spam filters)
    plain_text_fallback = (
        f"Request: {specialty_display}\n"
        f"Client: {request_obj.user.email}\n"
        "Please open this email in an HTML-compatible client to view the details."
    )

    return {
        "subject": subject,
        "body": plain_text_fallback,
        "html": body_html,
        "to": recipient_emails,
    }


def format_local_dt(dt):
    """Хелпер: конвертує UTC дату в локальний час і форматує рядок."""
    if not dt:
        return "-"
    # 🌟 Переводимо з UTC у локальний часовий пояс
    local_dt = timezone.localtime(dt) if timezone.is_aware(dt) else dt
    return local_dt.strftime("%d.%m.%Y %H:%M")
