from django.urls import path

from apps.chat import views

urlpatterns = [
    path(route="", view=views.ChatView.as_view(), name="index"),
    path(
        route="api/chat/",
        view=views.ChatMessageView.as_view(),
        name="chat-message",
    ),
    path(route="api/semesters/", view=views.SemestersView.as_view(), name="semesters"),
    path(
        route="api/semesters/<str:semester>/groups/",
        view=views.GroupsView.as_view(),
        name="groups",
    ),
    path(
        route="api/semesters/<str:semester>/groups/<int:group>/schedule/",
        view=views.ScheduleView.as_view(),
        name="schedule",
    ),
    path(
        route="api/professors/", view=views.ProfessorsView.as_view(), name="professors"
    ),
]
