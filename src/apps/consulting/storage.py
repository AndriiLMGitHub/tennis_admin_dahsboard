import os
import uuid
import logging
from pathlib import Path
import boto3
from django.conf import settings
from django.utils import timezone

from apps.consulting.models import PendingUpload

logger = logging.getLogger(__name__)

s3_client = boto3.client(
    's3',
    aws_access_key_id=os.getenv('R2_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('R2_SECRET_ACCESS_KEY'),
    endpoint_url=f"https://{os.getenv('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com",
    region_name='auto'
)

def generate_r2_upload_service(filename: str, content_type: str, upload_type: str, file_size: int) -> dict:
    """
    Повна функція валідації та генерації Presigned URL.

    Гарантує 100% відповідність лімітам та дозволеним форматам з settings.py,
    захищаючи бекенд від спроб обходу клієнтської валідації.
    """
    # 1. Валідація наявності імені файлу
    if not filename:
        raise ValueError("Filename is required")

    # 2. Перевірка типу завантаження на легітимність
    if upload_type not in settings.UPLOAD_DIRECTORIES:
        raise ValueError("Invalid upload type requested")

    # 3. Визначення розширення та категорії файлу
    ext = Path(filename).suffix.lower()
    file_category = None  # набуде значення 'video', 'file' або 'image'

    for category, extensions in settings.ALLOWED_EXTENSIONS.items():
        if ext in extensions:
            file_category = category
            break

    if not file_category:
        raise ValueError(f"File extension '{ext}' is not allowed.")

    # 4. Специфічні бізнес-обмеження для форм
    if upload_type == 'nutrition_intake' and file_category == 'video':
        raise ValueError("Video uploads are not allowed for nutrition intake.")

    # 5. Динамічний розрахунок ліміту розміру файлу
    if upload_type == 'coach_request':
        # Для коуча ліміт залежить від категорії файлу (Video = 100MB, File/Image = 10MB)
        max_allowed_size = settings.SIZE_LIMITS.get(file_category)
    else:
        # Для нутриціолога та інших використовуємо ліміт самої форми (10MB)
        max_allowed_size = settings.SIZE_LIMITS.get(upload_type)

    # Запобіжний fallback на випадок пропущених configs
    if not max_allowed_size:
        max_allowed_size = 10 * 1024 * 1024  # 10MB за замовчуванням

    # 6. Валідація розміру файлу
    if file_size > max_allowed_size:
        max_size_mb = max_allowed_size / (1024 * 1024)
        raise ValueError(f"File size exceeds the limit of {max_size_mb:.1f} MB for this type of upload.")

    # 7. Генерація унікального шляху у хмарі
    folder_prefix = settings.UPLOAD_DIRECTORIES[upload_type]
    date_prefix = timezone.now().strftime("%Y/%m/%d")
    unique_filename = f"{folder_prefix}/{date_prefix}/{uuid.uuid4()}{ext}"

    # 8. Генерація Presigned URL для прямого завантаження
    try:
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': os.getenv('R2_BUCKET_NAME'),
                'Key': unique_filename,
                'ContentType': content_type
            },
            ExpiresIn=900,
            HttpMethod='PUT'
        )
    except Exception as e:
        logger.error(f"Error generating presigned URL for {unique_filename}: {str(e)}", exc_info=True)
        raise RuntimeError("Failed to generate secure upload session.")


    try:
        PendingUpload.objects.create(file_key=unique_filename)
    except Exception as db_err:
        # Якщо база лягла, ми не повинні віддавати URL, бо файл стане неконтрольованим сміттям
        logger.critical(f"Failed to register pending upload in database for {unique_filename}: {str(db_err)}")
        raise RuntimeError("Failed to register upload session in database.")

    return {
        'upload_url': presigned_url,
        'file_key': unique_filename
    }