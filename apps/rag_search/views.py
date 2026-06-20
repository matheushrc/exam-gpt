from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.rag_search.search import search


class SearchView(APIView):
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="q",
                type=str,
                location=OpenApiParameter.QUERY,
                required=True,
            ),
            OpenApiParameter(
                name="materia",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
            ),
            OpenApiParameter(
                name="top_k",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
            ),
        ],
        responses={200: {"type": "array", "items": {"type": "object"}}},
    )
    def get(self, request):
        query = request.query_params.get("q")
        if not query:
            return Response(
                {"detail": "Query parameter 'q' is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        top_k = request.query_params.get("top_k")
        try:
            parsed_top_k = int(top_k) if top_k else None
        except ValueError:
            return Response(
                {"detail": "Query parameter 'top_k' must be an integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        results = search(
            query=query,
            materia=request.query_params.get("materia"),
            **({"top_k": parsed_top_k} if parsed_top_k is not None else {}),
        )

        return Response(
            [
                {
                    "score": score,
                    "questao": {
                        "id": str(questao.id),
                        "numero": questao.numero,
                        "enunciado": questao.enunciado,
                        "subquestoes": questao.subquestoes,
                        "resposta": questao.resposta,
                        "pontuacao": questao.pontuacao,
                    },
                }
                for score, questao in results
            ]
        )
