from django.urls import path
from . import views

urlpatterns = [
    path("select-role/", views.select_role, name="select_role"),
    path("register/coach/", views.register_coach_view, name="register_coach"),

    # Routing for student or coach
    path('profile/redirect/', views.profile_router_view, name='profile_router'),

    # Student profile urls
    path("student/profile/", views.student_profile_view, name="student_profile"),
    path('student/profile/edit/', views.student_profile_edit_view, name="student_profile_edit"),
    path(
        "student/profile/security/",
        views.common_profile_security_view,
        {
            'expected_role': 'Student',
            'template_name': 'dashboard/student/profile/security.html',
            'redirect_url_name': 'student_profile_security'
        },
        name="student_profile_security"
    ),
    path(
        "student/profile/deactivate/",
        views.deactivate_account_view,
        {'expected_role': 'Student'},
        name="student_deactivate_account"
    ),

    # Coach profile urls
    path("coach/profile/", views.coach_profile_view, name="coach_profile"),
    path('coach/profile/edit/', views.coach_profile_edit_view, name="coach_profile_edit"),
    path(
        "coach/profile/security/",
        views.common_profile_security_view,
        {
            'expected_role': 'Coach',
            'template_name': 'dashboard/coach/profile/security.html',  # Вкажи свій точний шлях до шаблону коуча
            'redirect_url_name': 'coach_profile_security'
        },
        name="coach_profile_security"
    ),
    path(
        "coach/profile/deactivate/",
        views.deactivate_account_view,
        {'expected_role': 'Coach'},
        name="coach_deactivate_account"
    ),
]
