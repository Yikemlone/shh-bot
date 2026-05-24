from unittest.mock import MagicMock, AsyncMock
import pytest
from cogs.commands import BasicCommands


class TestBasicCommands:
    @pytest.fixture
    def cog(self, tmp_path):
        c = BasicCommands(MagicMock())
        c.resource_path = str(tmp_path)
        return c

    @pytest.mark.asyncio
    async def test_ping(self, cog):
        cog.bot.latency = 0.042
        interaction = MagicMock()
        interaction.response.send_message = AsyncMock()
        await cog._ping.callback(cog, interaction)
        interaction.response.send_message.assert_called_once_with("Pong! 42ms")

    @pytest.mark.asyncio
    async def test_8ball_happy(self, cog, tmp_path):
        (tmp_path / "8ball-response.txt").write_text("Yes\nNo\n")
        interaction = MagicMock()
        interaction.response.send_message = AsyncMock()
        await cog._8ball.callback(cog, interaction, "test?")
        interaction.response.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_8ball_file_not_found(self, cog):
        interaction = MagicMock()
        interaction.response.send_message = AsyncMock()
        await cog._8ball.callback(cog, interaction, "q?")
        interaction.response.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_ez_not_monkey(self, cog):
        import os
        monkey = os.environ.get("MONKEY", "someone")
        interaction = MagicMock()
        interaction.user.global_name = monkey + "x"
        interaction.response.send_message = AsyncMock()
        await cog.ez.callback(cog, interaction)
        interaction.response.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_spam_not_spamming(self, cog):
        interaction = MagicMock()
        interaction.response.send_message = AsyncMock()
        await cog.stop_spam.callback(cog, interaction)
        interaction.response.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_spam_no_role(self, cog):
        interaction = MagicMock()
        interaction.user.roles = []
        interaction.response.send_message = AsyncMock()
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()
        await cog.spam.callback(cog, interaction)
        interaction.followup.send.assert_called_once()


@pytest.mark.asyncio
async def test_commands_setup():
    bot = MagicMock()
    bot.add_cog = AsyncMock()
    from cogs.commands import setup
    await setup(bot)
    bot.add_cog.assert_awaited_once()
