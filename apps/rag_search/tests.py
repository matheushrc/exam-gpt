from unittest.mock import patch

from django.test import SimpleTestCase
from django.urls import reverse
from rest_framework.test import APIClient


class SearchViewTests(SimpleTestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_search_requires_query(self) -> None:
        response = self.client.get(reverse("search"))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(), {"detail": "Query parameter 'q' is required."}
        )

    def test_search_rejects_invalid_top_k(self) -> None:
        response = self.client.get(reverse("search"), {"q": "tcp", "top_k": "many"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            {"detail": "Query parameter 'top_k' must be an integer."},
        )

    @patch("apps.rag_search.views.search")
    def test_search_returns_ranked_questions(self, search_mock) -> None:
        questao = type(
            "QuestaoStub",
            (),
            {
                "id": "abc123",
                "numero": 1,
                "enunciado": "Explique o TCP slow start.",
                "subquestoes": [],
                "resposta": "A janela de congestionamento cresce exponencialmente.",
                "pontuacao": 2.0,
            },
        )()
        search_mock.return_value = [(0.91, questao)]

        response = self.client.get(
            reverse("search"),
            {"q": "tcp slow start", "materia": "redes", "top_k": "3"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            [
                {
                    "score": 0.91,
                    "questao": {
                        "id": "abc123",
                        "numero": 1,
                        "enunciado": "Explique o TCP slow start.",
                        "subquestoes": [],
                        "resposta": "A janela de congestionamento cresce exponencialmente.",
                        "pontuacao": 2.0,
                    },
                }
            ],
        )
        search_mock.assert_called_once_with(
            query="tcp slow start",
            materia="redes",
            top_k=3,
        )
