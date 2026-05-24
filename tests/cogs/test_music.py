from unittest.mock import MagicMock, AsyncMock
import pytest
from cogs.music import Music


class TestMusic:
    @pytest.fixture
    def cog(self):
        from services.music.queue import QueueManagerService
        from services.voice.clientmanager import VoiceClientManagerService
        from services.music.song import SongService
        bot = MagicMock()
        c = Music(bot)
        return c

    def test_init(self, cog):
        assert cog.queue_manager is not None
        assert cog.voice_manager is not None
        assert cog.song_service is not None

    @pytest.mark.asyncio
    async def test_leave_disconnects(self, cog):
        cog.voice_manager.get_channel = MagicMock(return_value="channel")
        cog.voice_manager.disconnect = AsyncMock()
        cog.queue_manager.reset_queue = MagicMock()
        interaction = MagicMock()
        interaction.response.send_message = AsyncMock()
        await cog.leave.callback(cog, interaction)
        cog.voice_manager.disconnect.assert_awaited_once()
        interaction.response.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_skip_updates_queue(self, cog):
        cog.queue_manager.get_current_song = MagicMock(return_value={"song": "S1", "name": "A"})
        cog.queue_manager.get_song_queue = MagicMock(return_value=[{"song": "S2", "name": "B"}])
        cog.voice_manager.stop = MagicMock()
        interaction = MagicMock()
        interaction.response.send_message = AsyncMock()
        await cog.skip.callback(cog, interaction)
        interaction.response.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_pause_pauses(self, cog):
        cog.queue_manager.get_current_song = MagicMock(return_value={"song": "S", "name": "A"})
        cog.voice_manager.pause = MagicMock()
        interaction = MagicMock()
        interaction.response.send_message = AsyncMock()
        await cog.pause.callback(cog, interaction)
        cog.voice_manager.pause.assert_called_once()

    @pytest.mark.asyncio
    async def test_resume_resumes(self, cog):
        cog.queue_manager.get_current_song = MagicMock(return_value={"song": "S", "name": "A"})
        cog.song_service.get_song_source = MagicMock(return_value="source")
        cog.voice_manager.play = MagicMock()
        interaction = MagicMock()
        interaction.response.send_message = AsyncMock()
        await cog.resume.callback(cog, interaction)
        cog.voice_manager.play.assert_called_once_with("source")

    @pytest.mark.asyncio
    async def test_loop_toggles(self, cog):
        cog.queue_manager.isLooping = MagicMock(side_effect=[False, True])
        cog.queue_manager.toggleLooping = MagicMock()
        cog.queue_manager.reset_queue = MagicMock()
        interaction = MagicMock()
        interaction.response.send_message = AsyncMock()
        await cog.loop.callback(cog, interaction)
        cog.queue_manager.toggleLooping.assert_called_once()

    @pytest.mark.asyncio
    async def test_loop_off_resets_queue(self, cog):
        cog.queue_manager.isLooping = MagicMock(return_value=True)
        cog.queue_manager.toggleLooping = MagicMock()
        cog.queue_manager.reset_queue = MagicMock()
        interaction = MagicMock()
        interaction.response.send_message = AsyncMock()
        await cog.loop.callback(cog, interaction)
        cog.queue_manager.reset_queue.assert_called_once()

    @pytest.mark.asyncio
    async def test_queue_no_songs(self, cog):
        cog.queue_manager.isTherePlayableSongs = MagicMock(return_value=False)
        cog.queue_manager.get_current_song = MagicMock()
        interaction = MagicMock()
        interaction.response.send_message = AsyncMock()
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()
        await cog.queue.callback(cog, interaction)
        interaction.followup.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_after_playback_updates_queue(self, cog):
        cog.queue_manager.update_queue = MagicMock()
        cog.queue_manager.get_current_song = MagicMock(return_value={})
        cog.voice_manager.is_playing = MagicMock(return_value=False)
        cog.voice_manager.get_channel = MagicMock(return_value="ch")
        cog.voice_manager.get_voice_client = MagicMock(return_value="vc")
        cog.after_playback(None)

    @pytest.mark.asyncio
    async def test_play_current_song(self, cog):
        cog.song_service.prep_soung_source = MagicMock()
        cog.song_service.get_song_source = MagicMock(return_value="src")
        cog.voice_manager.play = MagicMock()
        cog.play_current_song("http://url")
        cog.song_service.prep_soung_source.assert_called_once_with("http://url")
        cog.voice_manager.play.assert_called_once_with("src", after=cog.after_playback)


@pytest.mark.asyncio
async def test_music_setup():
    bot = MagicMock()
    bot.add_cog = AsyncMock()
    from cogs.music import setup
    await setup(bot)
    bot.add_cog.assert_awaited_once()
