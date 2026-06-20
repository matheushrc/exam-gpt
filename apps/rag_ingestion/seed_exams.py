# ruff: noqa: E402
import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from apps.rag_ingestion.embed import DEFAULT_JSON_ROOT, seed_exam_jsons


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed all converted exam JSON files.")
    parser.add_argument(
        "--json-root",
        type=Path,
        default=DEFAULT_JSON_ROOT,
        help="JSON file or directory to ingest.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = seed_exam_jsons(args.json_root)
    print(
        f"Seeded {result.provas} exams, {result.questoes} questions, "
        f"{result.chunks} chunks. Index: {result.index_path}"
    )


if __name__ == "__main__":
    main()
