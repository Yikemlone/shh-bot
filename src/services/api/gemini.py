import os
import json
import asyncio
import re
from typing import Any
from google import genai
from google.genai import errors as genai_errors
from services.api.llm import LLMClient
from services.taskstore import Task
from core.logger import logging, SHH_BOT

logger = logging.getLogger(SHH_BOT)

SYSTEM_PROMPT = """You are a task extraction assistant. Given a voice transcript from a meeting or discussion, extract all actionable tasks.

For each task, provide:
- title: short clear title
- description: brief context
- priority: "low", "medium", "high", or "critical"
- labels: list of category tags (e.g. ["dev", "frontend"])
- epic: parent epic/story name if applicable (empty string if standalone)
- subtasks: list of sub-task descriptions (empty list if none)
- due_date: ISO date string if mentioned, otherwise empty string

Respond ONLY with a JSON object matching this schema:
{"tasks": [{"title": str, "description": str, "priority": str, "labels": list[str], "epic": str, "subtasks": list[str], "due_date": str}]}

If no tasks are found, return {"tasks": []}."""


def _extract_retry_delay(error_text: str) -> float:
    match = re.search(r"Please retry in ([\d.]+)s", error_text)
    if match:
        return float(match.group(1)) + 2.0
    return 10.0


class GeminiClient(LLMClient):

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set in environment")
        self._client = genai.Client(api_key=api_key)
        self._model = "gemini-2.0-flash"

    async def extract_tasks(self, transcript: str) -> list[Task]:
        if not transcript or not transcript.strip():
            return []

        try:
            result = await self._call_gemini(transcript)
            tasks_data = self._parse_response(result)
            return [
                Task(
                    id="",
                    title=t.get("title", "Untitled"),
                    description=t.get("description", ""),
                    priority=t.get("priority", "medium"),
                    labels=t.get("labels", []),
                    epic=t.get("epic", ""),
                    subtasks=t.get("subtasks", []),
                    due_date=t.get("due_date", ""),
                )
                for t in tasks_data
            ]
        except Exception as e:
            logger.error(f"Gemini task extraction failed: {e}")
            return []

    async def _call_gemini(self, transcript: str) -> dict[str, Any]:
        def _sync_call():
            return self._client.models.generate_content(
                model=self._model,
                contents=f"{SYSTEM_PROMPT}\n\nTranscript:\n{transcript}",
                config={
                    "response_mime_type": "application/json",
                    "temperature": 0.2,
                },
            )

        for attempt in range(4):
            try:
                response = await asyncio.to_thread(_sync_call)
                raw = response.text
                if raw:
                    try:
                        return json.loads(raw)
                    except json.JSONDecodeError:
                        logger.warning(f"Gemini returned invalid JSON: {raw[:200]}")
                return {}
            except genai_errors.ClientError as e:
                if e.code == 429:
                    delay = _extract_retry_delay(str(e))
                    logger.warning(
                        f"Gemini rate limited (attempt {attempt + 1}/4). "
                        f"Retrying in {delay:.0f}s..."
                    )
                    await asyncio.sleep(delay)
                    continue
                raise

        logger.error("Gemini rate limit retries exhausted")
        return {}

    @staticmethod
    def _parse_response(result: dict[str, Any]) -> list[dict[str, Any]]:
        if not result:
            return []
        tasks = result.get("tasks", [])
        if not isinstance(tasks, list):
            return []
        return tasks
