from unittest.mock import MagicMock, AsyncMock
import pytest
from cogs.shh import TypingCog


class TestTypingCog:
    @pytest.fixture
    def cog(self):
        return TypingCog(MagicMock())

    @pytest.mark.asyncio
    async def test_send_typing_messages(self, cog):
        channel = MagicMock()
        channel.send = AsyncMock()
        channel.typing = AsyncMock()
        user = MagicMock()
        user.display_avatar.url = "https://example.com/avatar.png"
        await cog.send_typing_messages(channel, user)
        assert channel.send.call_count >= 2


@pytest.mark.asyncio
async def test_shh_setup():
    bot = MagicMock()
    bot.add_cog = AsyncMock()
    from cogs.shh import setup
    await setup(bot)
    bot.add_cog.assert_awaited_once()
