from django.urls import path

from apps.upload import views

urlpatterns = [
    path("", views.UploadView.as_view(), name="upload"),
    path("<str:session_id>/meta/", views.MetaView.as_view(), name="upload-meta"),
    path("<str:session_id>/review/", views.ReviewView.as_view(), name="upload-review"),
    path(
        "api/professors/",
        views.ProfessorsPartialView.as_view(),
        name="upload-professors",
    ),
]
