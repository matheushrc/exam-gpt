import bs4
import requests
from django.views.generic import TemplateView
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

HORARIO_ENDPOINT = "https://cc.uffs.edu.br/horario/"
GROUPS_ENDPOINT = "https://cc.uffs.edu.br/horario/data/{semester}/groups.json"
SCHEDULE_ENDPOINT = "https://cc.uffs.edu.br/horario/data/{semester}/schedule.json"


def get_semesters() -> list[str]:
    response = requests.get(url=HORARIO_ENDPOINT)
    soup = bs4.BeautifulSoup(response.text, "html.parser")
    select = soup.find("select", attrs={"name": "semester", "id": "semester"})
    return [opt.text for opt in select.find_all("option")] if select else []


def get_groups(semester: str) -> list[dict]:
    response = requests.get(url=GROUPS_ENDPOINT.format(semester=semester))
    return response.json()


def get_schedule(semester: str, group: int) -> list[dict]:
    response = requests.get(url=SCHEDULE_ENDPOINT.format(semester=semester))

    schedule = [
        {
            **schedule,
        }
        for schedule in response.json()
        if schedule["group"] == group
    ]

    return schedule


class IndexView(TemplateView):
    template_name = "index.html"

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
