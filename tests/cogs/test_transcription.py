from unittest.mock import MagicMock, AsyncMock, patch
import pytest


class TestTranscription:
    @pytest.fixture
    def cog(self, mocker):
        mocker.patch("services.voice.recorder.WhisperModel.__init__", return_value=None)
        from cogs.transcription import Transcription
        bot = MagicMock()
        bot.loop = MagicMock()
        return Transcription(bot)

    @pytest.mark.asyncio
    async def test_record_no_voice(self, cog):
        interaction = MagicMock()
        interaction.user.voice = None
        interaction.response.send_message = AsyncMock()
        await cog.record.callback(cog, interaction)
        interaction.response.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_already_recording(self, cog):
        cog.transcription_service._recording = True
        interaction = MagicMock()
        interaction.guild.voice_client = MagicMock()
        interaction.user.voice.channel = interaction.guild.voice_client.channel
        interaction.response.send_message = AsyncMock()
        await cog.record.callback(cog, interaction)
        interaction.response.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_voice_client_exists_wrong_channel(self, cog):
        interaction = MagicMock()
        vc = MagicMock()
        vc.channel = "channel_a"
        interaction.guild.voice_client = vc
        interaction.user.voice.channel = "channel_b"
        interaction.response.send_message = AsyncMock()
        await cog.record.callback(cog, interaction)
        interaction.response.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_no_voice_client_connects(self, cog):
        ch = AsyncMock()
        ch.connect = AsyncMock(return_value=MagicMock())
        interaction = MagicMock()
        interaction.guild.voice_client = None
        interaction.user.voice.channel = ch
        interaction.response.send_message = AsyncMock()
        interaction.response.defer = MagicMock()
        cog.bot.loop = MagicMock()
        await cog.record.callback(cog, interaction)
        interaction.response.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_no_voice_client(self, cog):
        interaction = MagicMock()
        interaction.guild.voice_client = None
        interaction.response.send_message = AsyncMock()
        await cog.stop.callback(cog, interaction)
        interaction.response.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_not_recording(self, cog):
        interaction = MagicMock()
        interaction.guild.voice_client = MagicMock()
        interaction.response.send_message = AsyncMock()
        await cog.stop.callback(cog, interaction)
        interaction.response.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_transcription_setup():
    bot = MagicMock()
    bot.add_cog = AsyncMock()
    from cogs.transcription import setup
    await setup(bot)
    bot.add_cog.assert_awaited_once()
