from django.urls import path
from apps.consulting.views import student_views


urlpatterns = [
    path('requests/', student_views.list_students_requests_view, name='student_list_requests'),
    path('requests/<int:request_id>/', student_views.student_request_detail_view, name='student_request_detail'),
    path('requests/create/', student_views.create_request_view, name='student_create_request'),

    # For performance upload
    path('coaches/', student_views.list_coaches_view, name='student_list_coaches'),
    path('files/', student_views.files_attach_view, name='files_attach'),

    # Generate upload url for r2
    path('media/generate-upload-url/', student_views.generate_r2_upload_url, name='generate_r2_upload_url'),

    path('report/<int:report_id>/download-docx/', student_views.generate_report_docx_view, name='generate_report_docx'),

]