from django.db import models, transaction
from apps.consulting.utils import force_delete_from_r2 # або твоя функція видалення

class RequestQuerySet(models.QuerySet):
    def delete(self):
        """
        Масове видалення: 100% гарантія збору і знищення всіх файлів
        як з Media (теніс), так і з NutritionIntake (нутриціологія) перед видаленням з БД.
        """
        # 1. Збираємо файли з медіа (теніс/відео тощо)
        media_keys = set(
            self.filter(media__isnull=False)
            .values_list('media__file', flat=True)
        )

        # 2. Збираємо файли з анкет нутриціолога (attachments)
        nutrition_keys = set(
            self.filter(nutrition_intake__isnull=False)
            .values_list('nutrition_intake__attachments', flat=True)
        )

        # Об'єднуємо всі ключі в єдину множину без дублікатів
        all_keys = media_keys.union(nutrition_keys)

        # 3. Видаляємо самі запити з БД (CASCADE автоматично зітре NutritionIntake та Media)
        deleted_count, obj_slices = super().delete()

        # 4. Відправляємо запити на фізичне видалення в R2 ТІЛЬКИ після успішного коміту в БД
        if all_keys:
            transaction.on_commit(
                lambda: [force_delete_from_r2(key) for key in all_keys if key]
            )

        return deleted_count, obj_slices


class RequestManager(models.Manager):
    def get_queryset(self):
        return RequestQuerySet(self.model, using=self._db)