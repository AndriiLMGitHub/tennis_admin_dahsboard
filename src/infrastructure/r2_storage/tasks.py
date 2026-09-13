import os
import logging
from datetime import timedelta
import boto3
from celery import shared_task
from django.utils import timezone
from botocore.exceptions import BotoCoreError, ClientError

from apps.consulting.models import PendingUpload

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    ignore_result=True,
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_kwargs={'countdown': 60},
    autoretry_for=(BotoCoreError, ClientError),
    soft_time_limit=300,
    time_limit=360
)
def clear_orphaned_r2_uploads(self):
    """
    Періодична задача для видалення осиротілих файлів із Cloudflare R2.
    """
    threshold = timezone.now() - timedelta(seconds=1)

    logger.info(f"Starting R2 cleanup scan. Looking for records older than: {threshold}")

    orphaned_records = PendingUpload.objects.filter(created_at__lt=threshold)
    total_found = orphaned_records.count()

    logger.info(f"Database analysis finished. Found {total_found} orphaned records in PendingUpload table.")

    if total_found == 0:
        return "No orphaned files found to clean (Database query returned 0)."

    s3_client = boto3.client(
        's3',
        aws_access_key_id=os.getenv('R2_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('R2_SECRET_ACCESS_KEY'),
        endpoint_url=f"https://{os.getenv('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com",
        region_name='auto'
    )

    bucket_name = os.getenv('R2_BUCKET_NAME')
    deleted_count = 0

    for record in orphaned_records:
        try:
            logger.info(f"Attempting to physically delete from R2: {record.file_key}")

            # 1. Фізично видаляємо файл з Cloudflare R2
            s3_client.delete_object(Bucket=bucket_name, Key=record.file_key)

            # 2. Видаляємо запис із нашого тимчасового журналу
            logger.info(f"R2 delete success. Removing DB row ID: {record.id}")
            record.delete()
            deleted_count += 1

        except Exception as e:
            logger.error(f"Failed to delete record {record.file_key}. Error: {str(e)}", exc_info=True)
            continue

    logger.info(f"Cleanup finished. Successfully deleted {deleted_count} out of {total_found} files.")
    return f"Successfully cleared {deleted_count} orphaned files from Cloudflare R2."