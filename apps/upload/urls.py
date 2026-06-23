from django.urls import path

from apps.upload import views

urlpatterns = [
    path("", views.UploadView.as_view(), name="upload"),
]
