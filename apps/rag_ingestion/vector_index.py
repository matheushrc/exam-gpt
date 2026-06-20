from pathlib import Path

from turbovec import IdMapIndex

from apps.rag_ingestion.settings import embeddings_settings

INDEX_PATH = Path(embeddings_settings.INDEX_PATH)


def remove_turbo_ids(turbo_ids: list[int], *, index_path: Path = INDEX_PATH) -> None:
    if not turbo_ids or not index_path.exists():
        return

    index = IdMapIndex.load(str(index_path))
    for turbo_id in turbo_ids:
        index.remove(turbo_id)
    index.write(str(index_path))
