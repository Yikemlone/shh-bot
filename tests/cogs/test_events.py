from unittest.mock import MagicMock, AsyncMock
import pytest
from cogs.events import Events


class TestEvents:
    @pytest.fixture
    def cog(self):
        return Events(MagicMock())

    @pytest.mark.asyncio
    async def test_on_message_edit_skips_bots(self, cog):
        before = MagicMock()
        before.author.bot = True
        await cog.on_message_edit(before, MagicMock())

    @pytest.mark.asyncio
    async def test_on_message_edit_skips_same_content(self, cog):
        before = MagicMock()
        before.author.bot = False
        before.content = "hello"
        after = MagicMock()
        after.author.bot = False
        after.content = "hello"
        await cog.on_message_edit(before, after)

    @pytest.mark.asyncio
    async def test_on_message_edit_sends_diff(self, cog):
        before = MagicMock()
        before.author.bot = False
        before.author.mention = "<@1>"
        before.content = "old"
        after = MagicMock()
        after.author.bot = False
        after.content = "new"
        after.channel.send = AsyncMock()
        await cog.on_message_edit(before, after)
        after.channel.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_member_join(self, cog):
        import discord
        member = MagicMock()
        channel = AsyncMock()
        with pytest.MonkeyPatch().context() as mp:
            mp.setattr(discord.utils, "get", lambda *a, **kw: channel)
            await cog.on_member_join(member)
            channel.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_member_remove(self, cog):
        import discord
        member = MagicMock()
        channel = AsyncMock()
        with pytest.MonkeyPatch().context() as mp:
            mp.setattr(discord.utils, "get", lambda *a, **kw: channel)
            await cog.on_member_remove(member)
            channel.send.assert_called_once()


@pytest.mark.asyncio
async def test_events_setup():
    bot = MagicMock()
    bot.add_cog = AsyncMock()
    from cogs.events import setup
    await setup(bot)
    bot.add_cog.assert_awaited_once()
