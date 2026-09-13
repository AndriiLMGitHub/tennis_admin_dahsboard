from django.urls import path
from apps.consulting.views import superadmin_views

urlpatterns = [
    path('coaches/', superadmin_views.list_coaches_view, name='list_coaches'),
    path('students/', superadmin_views.list_students_view, name='list_students'),
    path('requests/', superadmin_views.list_requests_view, name='list_requests'),
    path('emails/', superadmin_views.list_emails_view, name='list_emails'),
]