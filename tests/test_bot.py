from unittest.mock import MagicMock, AsyncMock
import pytest


@pytest.mark.asyncio
async def test_bot_loads_cogs():
    import os
    import bot as bot_module
    bot_module.bot = MagicMock()
    bot_module.bot.load_extension = AsyncMock()
    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(os, "listdir", lambda path: ["music.py", "admin.py", "__init__.py", "events.py"])
        await bot_module.load_extensions()
        assert bot_module.bot.load_extension.call_count == 6
