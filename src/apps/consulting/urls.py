from django.urls import path, include
from apps.consulting.views import api

urlpatterns = [
    # API
    path('api/schedule/request/<int:pk>/mark-viewed/', api.mark_request_as_viewed_view, name='mark_request_viewed'),

    # All requests starting with /student/ go to student_urls.py
    path('student/', include('apps.consulting.consulting_urls.student_urls')),

    # All requests starting with /coach/ go to coach_urls.py
    path('coach/', include('apps.consulting.consulting_urls.coach_urls')),

    # All routes for psychology /psychology/ dashboard
    path('psychology/', include('apps.consulting.consulting_urls.psychology_urls')),

    # All routes for nutrition /nutrition/ dashboard
    path('nutrition/', include('apps.consulting.consulting_urls.nutrition_urls')),

    # All requests starting with /superadmin/ go to superadmin_urls.py
    path('superadmin/', include('apps.consulting.consulting_urls.superadmin_urls')),
]