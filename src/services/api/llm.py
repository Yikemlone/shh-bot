from abc import ABC, abstractmethod
from services.taskstore import Task


class LLMClient(ABC):

    @abstractmethod
    async def extract_tasks(self, transcript: str) -> list[Task]:
        ...
