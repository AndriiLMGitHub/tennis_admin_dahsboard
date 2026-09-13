import os
import random

from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from apps.consulting.decorators import nutrition_required
from apps.consulting.enums import Specialty
from apps.consulting.models import NutritionIntake, Request
from apps.consulting.utils import format_local_dt

METRONIC_COLORS = (
    'fc-event-primary',
    'fc-event-success',
    'fc-event-warning',
    'fc-event-info',
    'fc-event-danger',
    'fc-event-dark',
)


def _get_intake_val(intake, attr_name: str, suffix: str = "") -> str:
    """Безпечно витягує атрибут з анкети та додає суфікс (наприклад 'kg'), якщо значення існує."""
    if not intake:
        return "-"
    val = getattr(intake, attr_name, None)
    return f"{val}{suffix}" if val is not None and val != "" else "-"


def _serialize_request_to_event(item: Request) -> dict:
    """Трансформує об'єкт Request та пов'язану анкету в формат події FullCalendar."""
    intake = getattr(item, 'nutrition_intake', None)

    # 1. Обробка прикріпленого файлу
    file_url, file_name = None, None
    if intake and intake.attachments:
        try:
            file_url = intake.attachments.url
            file_name = os.path.basename(intake.attachments.name)
        except (ValueError, AttributeError):
            file_url, file_name = None, None

    # 2. Визначення та локалізація дат
    appointment_dt = getattr(intake, 'appointment_date', None)
    start_dt_val = getattr(intake, 'start_date', None)
    end_dt_val = getattr(intake, 'end_date', None)

    start_dt = appointment_dt or start_dt_val or item.created_at
    start_iso = (
        timezone.localtime(start_dt).isoformat()
        if start_dt and timezone.is_aware(start_dt)
        else (start_dt.isoformat() if start_dt else None)
    )

    # 3. Формування імені клієнта
    user_name = item.user.get_full_name() if item.user else ""
    client_title = (
            (intake.full_name if intake else None)
            or user_name
            or getattr(item.user, 'username', '')
            or f"Request #{item.id}"
    )

    # 4. Детермінований колір на основі ID (не змінюється при F5)
    event_class = METRONIC_COLORS[item.id % len(METRONIC_COLORS)]

    return {
        "id": item.id,
        "title": client_title,
        "start": start_iso,
        "className": event_class,
        "extendedProps": {
            "is_viewed": item.is_viewed,
            "full_name": client_title,
            "age": _get_intake_val(intake, "age"),
            "weight": _get_intake_val(intake, "weight", " kg"),
            "height": _get_intake_val(intake, "height", " cm"),
            "whatsapp_number": _get_intake_val(intake, "whatsapp_number"),
            "language": _get_intake_val(intake, "language"),

            # Дати
            "appointment_date": format_local_dt(appointment_dt),
            "start_date": format_local_dt(start_dt_val),
            "end_date": format_local_dt(end_dt_val),

            # Медичний анамнез
            "complaints": (intake.complaints if intake and intake.complaints else None) or str(
                _("No complaints provided")),
            "chronic_diseases": _get_intake_val(intake, "chronic_diseases"),
            "medications": _get_intake_val(intake, "medications_and_vitamins"),
            "allergies": _get_intake_val(intake, "allergies"),
            "operations": _get_intake_val(intake, "operations"),
            "traumas": _get_intake_val(intake, "traumas"),

            # Файл
            "file_url": file_url,
            "file_name": file_name,
        }
    }


@nutrition_required
def nutrition_view(request):
    """Головний дашборд нутриціолога (загальна сторінка/огляд)."""
    return render(request, 'dashboard/nutrition/nutrition.html')


@nutrition_required
def nutrition_schedule_view(request):
    """Календар та розклад консультацій нутриціолога."""

    # Пряма фільтрація по Enum (ORM Django обробляє це нативно)
    requests_qs = Request.objects.filter(
        assigned_specialist=request.user,
        specialty_needed=Specialty.NUTRITION
    ).select_related('user', 'service', 'nutrition_intake')

    events_data = [_serialize_request_to_event(item) for item in requests_qs]

    return render(request, 'dashboard/nutrition/schedule.html', {'events_data': events_data})
