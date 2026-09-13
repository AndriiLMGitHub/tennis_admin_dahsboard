from django.db import models
from django.utils.translation import gettext_lazy as _

class Specialty(models.TextChoices):
    TENNIS = 'TENNIS', _('Tennis Coach')
    NUTRITION = 'NUTRITION', _('Nutritionist')
    PSYCHOLOGY = 'PSYCHOLOGY', _('Psychologist')