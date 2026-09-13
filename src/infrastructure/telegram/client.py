import logging

from requests import Session
from pathlib import Path

logger = logging.getLogger(__name__)


class TelegramClient:
    """Оптимізований клієнт для взаємодії з Telegram Bot API."""

    def __init__(self, token: str):
        if not token:
            raise ValueError("Telegram Bot Token must be provided")
        self._base_url = f"https://api.telegram.org/bot{token}"
        # Сесія створюється один раз і НЕ закривається після кожного запиту
        self.session = Session()

    @staticmethod
    def _log_error(chat_id: str, error: Exception) -> None:
        """Внутрішній метод логування."""
        logger.error(f"Failed to send media to chat {chat_id}. Error: {type(error).__name__} - {error}")

    def send_document(self, chat_id: str, file_path: str) -> None:
        """
        Відправляє файл.
        Покладається на механізм retry від Celery замість urllib3.
        """
        path = Path(file_path)
        if not path.is_file():
            error = FileNotFoundError(f"File not found or is not a file: {file_path}")
            self._log_error(chat_id, error)
            raise error

        url = f"{self._base_url}/sendDocument"

        try:
            # Не використовуємо 'with self.session', щоб не закрити її
            with path.open('rb') as f:
                response = self.session.post(
                    url,
                    data={'chat_id': chat_id},
                    files={'document': f},
                    timeout=(5, 60)  # 5s connect, 60s read
                )
            response.raise_for_status()
        except Exception as exc:
            self._log_error(chat_id, exc)
            raise
