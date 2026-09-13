import os

from celery import shared_task
from requests.exceptions import RequestException

from infrastructure.telegram.client import TelegramClient

# ==========================================
# Оптимізація для Celery Workers
# ==========================================
# Ініціалізуємо клієнт на рівні модуля.
# Коли Celery worker запускається (fork), він створить цей об'єкт один раз.
# Усі виконання таски send_media_to_telegram_task у цьому worker будуть
# reuse одне HTTP-з'єднання (Session).
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
telegram_client = TelegramClient(TELEGRAM_TOKEN) if TELEGRAM_TOKEN else None


@shared_task(bind=True, max_retries=3)
def send_media_to_telegram_task(self, file_path: str, target_chat_id: str) -> None:
    """
    Задача для відправки медіафайлу.
    Якщо API Telegram відхиляє запит (429, 500+), Celery спробує ще раз через 60 секунд.
    """
    if not telegram_client:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set in environment.")

    try:
        telegram_client.send_document(target_chat_id, file_path)
    except RequestException as exc:
        # RequestException покриває всі мережеві помилки та проблеми з HTTP.
        # countdown=60 можна зробити експоненційним: countdown=2 ** self.request.retries * 60
        raise self.retry(exc=exc, countdown=60)