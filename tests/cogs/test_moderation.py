from unittest.mock import MagicMock, AsyncMock
import pytest
from cogs.moderation import Moderation


class TestModeration:
    @pytest.fixture
    def cog(self):
        return Moderation(MagicMock())

    @pytest.mark.asyncio
    async def test_clear_purges(self, cog):
        interaction = MagicMock()
        interaction.response.send_message = AsyncMock()
        interaction.channel.purge = AsyncMock()
        await cog.clear.callback(cog, interaction, 5)
        interaction.channel.purge.assert_called_once_with(limit=5)
        interaction.response.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_moderation_setup():
    bot = MagicMock()
    bot.add_cog = AsyncMock()
    from cogs.moderation import setup
    await setup(bot)
    bot.add_cog.assert_awaited_once()
