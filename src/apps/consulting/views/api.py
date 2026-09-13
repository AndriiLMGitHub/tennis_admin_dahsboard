from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from apps.consulting.models import Request


@login_required
@require_POST
def mark_request_as_viewed_view(request, pk):
    # Спочатку перевіряємо, чи взагалі існує такий запис і чи належить він спеціалісту.
    # Якщо ні - Django автоматично кине 404 Not Found (що ти побачиш у консолі браузера).
    req_obj = get_object_or_404(Request, pk=pk, assigned_specialist=request.user)

    # Якщо існує, атомарно оновлюємо тільки якщо is_viewed == False
    updated_count = Request.objects.filter(
        pk=pk,
        is_viewed=False
    ).update(is_viewed=True)

    return JsonResponse({
        "status": "success",
        "was_updated": bool(updated_count),
        "id": pk
    })
