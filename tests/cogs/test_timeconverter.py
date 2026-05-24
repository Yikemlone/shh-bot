from unittest.mock import MagicMock, AsyncMock
import pytest
from cogs.timeconverter import TimeConverter


class TestTimeConverter:
    def test_init(self):
        cog = TimeConverter(MagicMock())
        assert cog is not None


@pytest.mark.asyncio
async def test_timeconverter_setup():
    bot = MagicMock()
    bot.add_cog = AsyncMock()
    from cogs.timeconverter import setup
    await setup(bot)
    bot.add_cog.assert_awaited_once()
