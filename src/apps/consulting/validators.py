import logging
import os

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


logger = logging.getLogger(__name__)

def validate_media_file(media_type, file_obj=None):
    """
    Універсальний комерційний валідатор для моделі Media.

    ВАЖЛИВО: Має викликатися виключно всередині методу clean() моделі,
    оскільки потребує динамічного контексту media_type.
    """
    # 🚨 ЗАХИСТ ВІД СИГНАТУРНОГО ЗБОЮ DJANGO:
    # Якщо функцію викликав двигун Django через validators=[...], першим аргументом
    # прийде сам файл. Ми м'яко пропускаємо її, бо чистка все одно відбудеться в clean()
    if file_obj is None:
        return

    if not file_obj or not file_obj.name:
        return

    ext = os.path.splitext(file_obj.name)[1].lower()

    # --- 1. ВАЛІДАЦІЯ РОЗШИРЕННЯ ФАЙЛІВ (Офлайн) ---
    if media_type in settings.ALLOWED_EXTENSIONS:
        valid_extensions = settings.ALLOWED_EXTENSIONS[media_type]
        if ext not in valid_extensions:
            raise ValidationError(
                _("Unsupported format for %(type)s. Allowed formats: %(formats)s"),
                params={'type': media_type, 'formats': ', '.join(valid_extensions)}
            )

    # --- 2. ВАЛІДАЦІЯ РЕАЛЬНОГО РОЗМІРУ В ХМАРІ (Онлайн через HEAD) ---
    if media_type in settings.SIZE_LIMITS:
        max_allowed_size = settings.SIZE_LIMITS[media_type]

        try:
            # 1. 🛡️ ОПТИМІЗАЦІЯ: Перевіряємо, чи файл є "брудним" (зміненим)
            # Якщо _committed == True, це означає, що об'єкт завантажено з БД і файл не мінявся.
            # Ми просто пропускаємо перевірку, зберігаючи ресурси та час відгуку бази даних.
            if getattr(file_obj, '_committed', False) is True:
                return

            # 2. 🛡️ ОПТИМІЗАЦІЯ: Локальна перевірка для стандартного завантаження
            # Якщо файл завантажується локально (наприклад, через Django Admin), Django тримає його
            # в пам'яті (InMemoryUploadedFile). Його розмір відомий локально і нам НЕ потрібен мережевий запит.
            if hasattr(file_obj, 'file') and hasattr(file_obj.file, 'size'):
                actual_file_size = file_obj.file.size
            else:
                # 3. 🌐 ОСТАННІЙ РУБІЖ: Робимо запит до Cloudflare R2
                # Цей крок виконується лише для асинхронних завантажень, коли у нас є тільки рядок-ключ.
                actual_file_size = file_obj.storage.size(file_obj.name)

            # 4. Валідація ліміту
            if actual_file_size > max_allowed_size:
                max_size_mb = round(max_allowed_size / (1024 * 1024), 1)
                raise ValidationError(
                    _("The uploaded file is too large. Maximum allowed size for %(type)s is %(max_size)s MB."),
                    params={'type': media_type, 'max_size': max_size_mb}
                )

        except ValidationError:
            # Твої власні помилки валідації розміру прокидаємо далі без змін
            raise
        except Exception as e:
            # Логуємо реальну технічну помилку (наприклад, якщо користувач підробив запит і файлу в R2 немає)
            logger.error(
                f"Cloudflare R2 storage size verification failed for file '{file_obj.name}'. "
                f"Reason: {str(e)}",
                exc_info=True
            )
            # Користувачу повертаємо безпечний текст
            raise ValidationError(
                _("The file could not be verified. It may not have been uploaded to cloud storage correctly.")
            )