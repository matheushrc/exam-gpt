# from django.shortcuts import render
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic_ai.agent import Agent

from apps.rag_ingestion.agents.Google import GoogleAgent
from apps.rag_ingestion.prompts import EXAM_PROMPT
from apps.rag_ingestion.schemas import Prova
from apps.rag_ingestion.utils import load_images_from_folder

load_dotenv()


async def get_exam_data(google_client: GoogleAgent, images: list[bytes]):
    # Create your views here.

    agent: Agent[None, str] = google_client.create_agent(
        model_name="gemini-3.5-flash",
        retries=10,
        output_type=Prova,
        model_settings={
            "max_tokens": 64000,
            "temperature": 0.0,
        },
        system_prompt=EXAM_PROMPT,
    )

    result = await google_client.get_inference_async(
        agent=agent,
        image_content=images,
    )

    return result


if __name__ == "__main__":
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(
        description="Extract one exam image folder to JSON."
    )
    parser.add_argument("image_folder", type=Path)
    parser.add_argument("output_json", type=Path)
    args = parser.parse_args()

    GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
    google_client = GoogleAgent(api_key=GOOGLE_API_KEY)

    images = load_images_from_folder(str(args.image_folder))
    prova_data = asyncio.run(get_exam_data(google_client, images))
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("w", encoding="utf-8") as f:
        json.dump(prova_data.output.model_dump(), f, indent=4, ensure_ascii=False)
