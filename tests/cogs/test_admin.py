from unittest.mock import MagicMock, AsyncMock
import pytest
from cogs.admin import Cog as AdminCog


class TestAdminCog:
    @pytest.fixture
    def cog(self):
        return AdminCog(MagicMock())

    def test_check_if_cog_is_loaded_not_loaded(self, cog):
        assert not cog.check_if_cog_is_loaded("cogs.music")

    def test_check_if_cog_is_loaded_when_loaded(self, cog):
        cog.bot.extensions = {"cogs.music": object()}
        assert cog.check_if_cog_is_loaded("cogs.music")

    @pytest.mark.asyncio
    async def test_load_rejects_non_owner(self, cog):
        interaction = MagicMock()
        interaction.response.send_message = AsyncMock()
        interaction.user.id = 999
        interaction.guild.owner_id = 123
        # access the underlying function via the Command's callback
        await cog.load.callback(cog, interaction, "cogs.music")
        interaction.response.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_unload_rejects_non_owner(self, cog):
        interaction = MagicMock()
        interaction.response.send_message = AsyncMock()
        interaction.user.id = 999
        interaction.guild.owner_id = 123
        await cog.unload.callback(cog, interaction, "cogs.music")
        interaction.response.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_reload_rejects_non_owner(self, cog):
        interaction = MagicMock()
        interaction.response.send_message = AsyncMock()
        interaction.user.id = 999
        interaction.guild.owner_id = 123
        await cog.reload.callback(cog, interaction, "cogs.music")
        interaction.response.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_admin_setup():
    bot = MagicMock()
    bot.add_cog = AsyncMock()
    from cogs.admin import setup
    await setup(bot)
    bot.add_cog.assert_awaited_once()
