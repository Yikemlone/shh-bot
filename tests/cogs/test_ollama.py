from unittest.mock import MagicMock, AsyncMock
import pytest
from cogs.ollama import Ollama


@pytest.mark.asyncio
async def test_ollama_setup():
    bot = MagicMock()
    bot.add_cog = AsyncMock()
    from cogs.ollama import setup
    await setup(bot)
    bot.add_cog.assert_awaited_once()
