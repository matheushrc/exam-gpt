from django.urls import path

from apps.rag_search.views import SearchView

urlpatterns = [
    path(route="search/", view=SearchView.as_view(), name="search"),
]
