from django.db.models import Q, Model
from django.utils import timezone
from datetime import timedelta

from django.shortcuts import render
from django.contrib.auth import get_user_model
from apps.consulting.decorators import superuser_required
from apps.consulting.models import Request
from apps.feedback.models import Feedback

User = get_user_model()


@superuser_required
def list_requests_view(request):
    queryset = Request.objects.all().select_related('user', 'assigned_specialist', 'service')

    status_filter = request.GET.get('status', 'all')
    period_filter = request.GET.get('period', 'all')

    search_query = request.GET.get('search', '').strip()

    if search_query:
        queryset = queryset.filter(
            Q(user__email__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(service__name__icontains=search_query)
        )

    if status_filter != 'all' and status_filter in dict(Request.STATUS_CHOICES).keys():
        queryset = queryset.filter(status=status_filter)

    if period_filter != 'all':
        now = timezone.now()
        if period_filter == 'this_month':
            queryset = queryset.filter(created_at__year=now.year, created_at__month=now.month)
        elif period_filter == 'last_90_days':
            ninety_days_ago = now - timedelta(days=90)
            queryset = queryset.filter(created_at__gte=ninety_days_ago)
        elif period_filter == 'this_year':
            queryset = queryset.filter(created_at__year=now.year)

    total_requests_count = queryset.count()

    queryset = queryset.order_by('-created_at')

    context = {
        'all_requests': queryset,
        'total_requests_count': total_requests_count,  # Передаємо змінну в шаблон
    }
    return render(request, 'dashboard/admin/list_requests.html', context)


@superuser_required
def list_coaches_view(request):
    coaches = User.objects.filter(role='Coach')
    return render(request, 'dashboard/admin/list_coaches.html', {'coaches': coaches})


@superuser_required
def list_students_view(request):
    students = User.objects.filter(role='Student')
    return render(request, 'dashboard/admin/list_students.html', {'students': students})


@superuser_required
def list_emails_view(request):
    emails = Feedback.objects.all()
    return render(request, 'dashboard/admin/list_emails.html', {'emails': emails})
