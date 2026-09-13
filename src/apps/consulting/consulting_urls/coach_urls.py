from django.urls import path
from apps.consulting.views import coach_views

# Тут ми використовуємо префікс 'coach_'
urlpatterns = [
    path('requests/', coach_views.list_coach_requests_view, name='coach_list_requests'),
    path('requests/<int:request_id>', coach_views.request_coach_detail_view, name='coach_request_detail'),

]