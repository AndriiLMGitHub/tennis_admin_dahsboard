from django.urls import path
from apps.consulting.views import psychology_views as views

urlpatterns = [
    path('', views.psychology_view, name='psychology'),
    path('schedule/', views.psychology_schedule_view, name='psychology_schedule'),
]