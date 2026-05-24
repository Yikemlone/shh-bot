from unittest.mock import MagicMock, AsyncMock
import pytest
from cogs.gifspam import GifSpam


class TestGifSpam:
    @pytest.fixture
    def cog(self):
        return GifSpam(MagicMock())

    @pytest.mark.asyncio
    async def test_gif_time_no_perms(self, cog):
        interaction = MagicMock()
        interaction.user.roles = []
        interaction.user.guild_permissions.manage_messages = False
        interaction.user.guild_permissions.kick_members = False
        interaction.user.guild_permissions.ban_members = False
        interaction.user.guild_permissions.administrator = False
        interaction.response.send_message = AsyncMock()
        await cog.gif.callback(cog, interaction)
        assert not cog.gif_on

    @pytest.mark.asyncio
    async def test_on_message_skips_bots(self, cog):
        msg = MagicMock()
        msg.author.bot = True
        await cog.on_message(msg)


@pytest.mark.asyncio
async def test_gifspam_setup():
    bot = MagicMock()
    bot.add_cog = AsyncMock()
    from cogs.gifspam import setup
    await setup(bot)
    bot.add_cog.assert_awaited_once()
