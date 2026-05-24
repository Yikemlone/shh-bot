from unittest.mock import MagicMock, AsyncMock
import pytest
from cogs.japanese import Japanese


class TestJapanese:
    @pytest.fixture
    def cog(self):
        return Japanese(MagicMock())

    @pytest.mark.asyncio
    async def test_translate_sends_result(self, cog, mocker):
        mocker.patch("services.api.jisho.JapaneseConnection.get_data", return_value="Kanji: 猫")
        interaction = MagicMock()
        interaction.response.send_message = AsyncMock()
        await cog.translate.callback(cog, interaction, "cat")
        interaction.response.send_message.assert_called_once_with("Kanji: 猫")


@pytest.mark.asyncio
async def test_japanese_setup():
    bot = MagicMock()
    bot.add_cog = AsyncMock()
    from cogs.japanese import setup
    await setup(bot)
    bot.add_cog.assert_awaited_once()
