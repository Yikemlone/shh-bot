import os
import json
import asyncio
from typing import Any
from services.api.llm import LLMClient
from services.taskstore import Task
from core.logger import logging, SHH_BOT

logger = logging.getLogger(SHH_BOT)

SYSTEM_PROMPT = """Extract all tasks, action items, requests, and todos from the transcript. Be inclusive — turn anything that sounds like something someone intends to do, create, make, fix, build, or follow up on into a task.

For each task:
- title: clear short title
- description: brief context
- priority: "low", "medium", "high", or "critical"
- labels: category tags like ["dev"], ["frontend"], ["design"], ["chore"], etc.
- epic: parent story if mentioned (empty if standalone)
- subtasks: list of sub-steps if mentioned (empty if none)
- due_date: ISO date if mentioned, otherwise empty string

Respond ONLY with valid JSON:
{"tasks": [{"title": str, "description": str, "priority": str, "labels": list[str], "epic": str, "subtasks": list[str], "due_date": str}]}

Return {"tasks": []} only if there is genuinely nothing that could be a task."""


class OllamaClient(LLMClient):

    def __init__(self):
        self._model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct-q4_K_M")

    async def extract_tasks(self, transcript: str) -> list[Task]:
        if not transcript or not transcript.strip():
            return []

        try:
            result = await self._call_ollama(transcript)
            tasks_data = self._parse_response(result)
            tasks = [
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
            logger.info(f"Parsed {len(tasks)} tasks from Ollama response")
            return tasks
        except Exception as e:
            logger.error(f"Ollama task extraction failed: {e}")
            return []

    async def _call_ollama(self, transcript: str) -> dict[str, Any]:
        import ollama

        model = self._model
        logger.info(f"Calling ollama model {model}...")

        def _sync_call():
            response = ollama.chat(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Transcript:\n{transcript}"},
                ],
                options={"temperature": 0.2},
                format="json",
            )
            return response

        result = await asyncio.to_thread(_sync_call)
        content = result["message"]["content"]
        logger.info(f"Ollama response received ({len(content)} chars)")
        return json.loads(content)

    @staticmethod
    def _parse_response(result: dict[str, Any]) -> list[dict[str, Any]]:
        if not result:
            return []
        tasks = result.get("tasks", [])
        if not isinstance(tasks, list):
            return []
        return tasks
