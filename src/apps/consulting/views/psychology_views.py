# ==========================================
# PSYCHOLOGY VIEWS
# ==========================================
from django.shortcuts import render
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from apps.consulting.decorators import psychology_required
from apps.consulting.enums import Specialty
from apps.consulting.models import Request
from apps.consulting.utils import format_local_dt


METRONIC_COLORS = (
    'fc-event-primary',
    'fc-event-success',
    'fc-event-warning',
    'fc-event-info',
    'fc-event-dark',
)


def _get_text_val(intake, attr_name: str, fallback: str = "-") -> str:
    """Безпечно витягує текстове значення з анкети. Суфікси тут не потрібні."""
    if not intake:
        return fallback
    val = getattr(intake, attr_name, None)
    return str(val).strip() if val else fallback


def _serialize_request_to_event(item: Request) -> dict:
    """Трансформує об'єкт Request та PsychologyIntake у формат події FullCalendar."""
    intake = getattr(item, 'psychology_intake', None)

    # 1. Логіка дат (у психолога лише appointment_date)
    appointment_dt = getattr(intake, 'appointment_date', None)
    start_dt = appointment_dt or item.created_at

    start_iso = (
        timezone.localtime(start_dt).isoformat()
        if start_dt and timezone.is_aware(start_dt)
        else (start_dt.isoformat() if start_dt else None)
    )

    # 2. Формування імені клієнта
    user_name = item.user.get_full_name() if item.user else ""
    client_title = user_name or getattr(item.user, 'username', '') or f"Request #{item.id}"

    # 3. Візуальна логіка: жорстко маркуємо червоним, якщо криза
    is_crisis = getattr(intake, 'crisis_state', False) if intake else False
    if is_crisis:
        event_class = 'fc-event-danger'
    else:
        event_class = METRONIC_COLORS[item.id % len(METRONIC_COLORS)]

    return {
        "id": item.id,
        "title": client_title,
        "start": start_iso,
        "className": event_class,
        "extendedProps": {
            "is_viewed": item.is_viewed,
            "full_name": client_title,

            # Обов'язкові поля
            "whatsapp_number": _get_text_val(intake, "whatsapp_number"),
            "appointment_date": format_local_dt(appointment_dt),

            # Необов'язкові текстові поля (надаємо fallback значення)
            "primary_concern": _get_text_val(intake, "primary_concern", str(_("Not provided"))),
            "psychiatric_medications": _get_text_val(intake, "psychiatric_medications", str(_("None"))),

            # Булеві прапорці (передаються як є, для обробки в JS)
            "previous_therapy": getattr(intake, 'previous_therapy', False) if intake else False,
            "crisis_state": is_crisis,
        }
    }


@psychology_required
def psychology_view(request):
    """Головний дашборд психолога (загальна сторінка/огляд)."""
    return render(request, 'dashboard/psychology/index.html')


@psychology_required
def psychology_schedule_view(request):
    """Календар та розклад консультацій психолога."""
    specialty_val = Specialty.PSYCHOLOGY.value if isinstance(Specialty.PSYCHOLOGY, Specialty) else Specialty.PSYCHOLOGY

    # Використовуємо select_related для оптимізації SQL-запитів
    requests_qs = Request.objects.filter(
        assigned_specialist=request.user,
        specialty_needed=specialty_val
    ).select_related('user', 'service', 'psychology_intake')

    events_data = [_serialize_request_to_event(item) for item in requests_qs]

    return render(request, 'dashboard/psychology/psychology_schedule.html', {'events_data': events_data})