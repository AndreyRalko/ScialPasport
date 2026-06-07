from django.urls import path

from . import views

urlpatterns = [
    path("", views.student_list, name="student-list"),
    path("students/create/", views.student_create, name="student-create"),
    path("students/<int:pk>/", views.student_detail, name="student-detail"),
    path("students/<int:pk>/edit/", views.student_update, name="student-update"),
    path("students/<int:pk>/family/", views.family_edit, name="family-edit"),
    path("students/<int:pk>/family/member/create/", views.family_member_create, name="family-member-create"),
    path("students/<int:pk>/family/member/<int:member_id>/delete/", views.family_member_delete, name="family-member-delete"),
    path("students/<int:pk>/housing/", views.housing_edit, name="housing-edit"),
    path("students/<int:pk>/psycho/", views.psycho_edit, name="psycho-edit"),
    path("students/<int:pk>/academic/", views.academic_edit, name="academic-edit"),
    path("students/<int:pk>/medical/", views.medical_edit, name="medical-edit"),
    path("students/<int:pk>/benefits/", views.benefits_edit, name="benefits-edit"),
    path("students/<int:pk>/ai/generate/", views.ai_generate, name="ai-generate"),
    path("ai-analytics/", views.ai_analytics_page, name="ai-analytics"),
    path("reports/", views.reports_page, name="reports"),
    path("reports/export/<str:report_key>/<str:fmt>/", views.export_report, name="report-export"),
    path("action-logs/", views.action_logs, name="action-logs"),
    path("settings/", views.settings_page, name="settings"),
    path("settings/references/<str:key>/<int:pk>/edit/", views.reference_edit, name="reference-edit"),
    path("settings/references/<str:key>/<int:pk>/toggle/", views.reference_toggle, name="reference-toggle"),
    path("settings/users/create/", views.user_create, name="user-create"),
    path("settings/users/<int:pk>/edit/", views.user_edit, name="user-edit"),
]
