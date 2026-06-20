from django.views.generic import TemplateView
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.chat.cache import (
    get_groups,
    get_professors_for_materia,
    get_professors_for_semester,
    get_schedule,
    get_semesters,
)


class IndexView(TemplateView):
    template_name = "chat.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["semesters"] = get_semesters()
        semester = self.request.GET.get("semester")
        if semester:
            context["groups"] = get_groups(semester)
            context["selected_semester"] = semester
            group = self.request.GET.get("group")
            if group:
                context["selected_group"] = int(group)
                context["schedule"] = get_schedule(semester, int(group))

        return context


class SemestersView(APIView):
    @extend_schema(responses={200: {"type": "array", "items": {"type": "string"}}})
    def get(self, request):
        return Response(get_semesters())


class GroupsView(APIView):
    @extend_schema(responses={200: {"type": "array", "items": {"type": "object"}}})
    def get(self, request, semester: str):
        return Response(get_groups(semester))


class ScheduleView(APIView):
    @extend_schema(responses={200: {"type": "array", "items": {"type": "object"}}})
    def get(self, request, semester: str, group: int):
        return Response(get_schedule(semester, group))


class ProfessorsView(APIView):
    @extend_schema(responses={200: {"type": "array", "items": {"type": "object"}}})
    def get(self, request):
        semester = request.query_params.get("semester", "")
        materia = request.query_params.get("materia", "")
        if not semester:
            return Response([], status=200)
        if materia:
            professors = get_professors_for_materia(semester, materia)
        else:
            professors = get_professors_for_semester(semester)
        return Response(professors)
