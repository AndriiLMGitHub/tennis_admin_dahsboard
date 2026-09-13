# ==========================================
# COACH VIEWS
# ==========================================
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import PageNotAnInteger, EmptyPage, Paginator
from django.db import transaction
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth import get_user_model

from apps.consulting.decorators import coach_required
from apps.consulting.models import Request, Report
from django.utils.translation import gettext_lazy as _

User = get_user_model()

TEMPLATE_DIR = 'dashboard/coach/requests/'

@coach_required
def list_coach_requests_view(request):
    """
    """
    # 1. Вибірка заявок, ПРИЗНАЧЕНИХ цьому тренеру
    requests_coach_list = (
        Request.objects.filter(
            assigned_specialist=request.user,
        )
        # 2. ОПТИМІЗАЦІЯ: Підтягуємо 'user' (студента), а не 'specialist'
        .select_related('service', 'user')
        .order_by('-created_at')
    )

    coach_paginator = Paginator(requests_coach_list, 6)

    page_number = request.GET.get('page', '1')

    try:
        page_obj = coach_paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = coach_paginator.page(1)
    except EmptyPage:
        page_obj = coach_paginator.page(coach_paginator.num_pages)

    breadcrumbs = [
        {'name': _('My Requests'), 'url': None},
    ]

    context = {
        'requests': page_obj,
        'breadcrumbs': breadcrumbs,
    }

    return render(request, f'{TEMPLATE_DIR}list.html', context)



@coach_required
def request_coach_detail_view(request, request_id):
    # 1. ОПТИМІЗОВАНА ВИБІРКА
    request_item = get_object_or_404(
        Request.objects
        .prefetch_related('media')
        .select_related('service', 'user', 'report'),
        id=request_id,
        assigned_specialist=request.user
    )

    # 2. БЕЗПЕЧНЕ ОТРИМАННЯ ЗВІТУ
    try:
        report = getattr(request_item, 'report')
    except ObjectDoesNotExist:
        report = None

    if request.method == "POST":
        new_status = request.POST.get('status')
        pdf_file = request.FILES.get('pdf')

        # АНАЛІТИКА: Масив усіх текстових полів звіту.
        # Це єдине місце, яке треба буде змінити, якщо ти додаси нові поля в майбутньому.
        text_fields = [
            'overall_assessment', 'strength_1', 'strength_2', 'strength_3',
            'priority_1_issue', 'priority_1_why', 'priority_1_drill',
            'priority_2_issue', 'priority_2_why', 'priority_2_drill',
            'priority_3_issue', 'priority_3_why', 'priority_3_drill',
            'action_plan', 'text', 'external_link'
        ]

        # Збираємо всі дані зі словника POST, одночасно роблячи .strip().
        # Це захищає від "порожніх" збережень, коли користувач просто ввів пробіл.
        form_data = {field: request.POST.get(field, '').strip() for field in text_fields}

        try:
            with transaction.atomic():

                # А. ОНОВЛЕННЯ СТАТУСУ
                if new_status and new_status != request_item.status:
                    request_item.change_status(new_status, request.user)

                # Б. УМНЕ ЗБЕРЕЖЕННЯ ЗВІТУ
                # Перевіряємо, чи є хоча б одне непусте значення у словнику form_data АБО чи передано файл
                has_text_data = any(form_data.values())
                has_report_data = has_text_data or bool(pdf_file)

                if has_report_data or report:
                    if not report:
                        report = Report(request=request_item, created_by=request.user)

                    # Динамічно присвоюємо всі очищені текстові поля об'єкту моделі
                    for field, value in form_data.items():
                        setattr(report, field, value)

                    if pdf_file:
                        report.pdf = pdf_file

                    report.save()

            messages.success(request, _("Request updated successfully."))
            # Переконайся, що ім'я URL збігається з твоїм urls.py
            return redirect('coach_request_detail', request_id=request_item.id)

        except Exception as e:
            # У production варто додати логування помилки e
            messages.error(request, _("An error occurred while saving. Please try again."))

    context = {
        'request_item': request_item,
        'report': report,
    }

    return render(request, f'{TEMPLATE_DIR}detail.html', context)
