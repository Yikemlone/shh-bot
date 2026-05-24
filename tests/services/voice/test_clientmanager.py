import asyncio
import pytest
from services.voice.clientmanager import VoiceClientManagerService


def make_mock_vc(mocker):
    vc = mocker.Mock()
    vc.mode = "xsalsa20_poly1305"
    vc.ssrc = 12345
    vc.set_davey = mocker.Mock()
    return vc


def make_mock_channel(mocker):
    ch = mocker.AsyncMock()
    ch.name = "General"
    ch.connect = mocker.AsyncMock()
    return ch


class TestVoiceClientManagerService:
    @pytest.fixture
    def service(self):
        return VoiceClientManagerService()

    def test_initial_state(self, service):
        assert service.get_channel() is None
        assert service.get_voice_client() is None

    def test_set_channel_and_client(self, service, mocker):
        vc = make_mock_vc(mocker)
        service.channel = "test_channel"
        service.voice_client = vc
        assert service.voice_client == vc
        assert service.get_channel() == "test_channel"

    def test_stop_delegates(self, service, mocker):
        vc = make_mock_vc(mocker)
        service.voice_client = vc
        service.stop()
        vc.stop.assert_called_once()

    def test_pause_delegates(self, service, mocker):
        vc = make_mock_vc(mocker)
        service.voice_client = vc
        service.pause()
        vc.pause.assert_called_once()

    def test_resume_delegates(self, service, mocker):
        vc = make_mock_vc(mocker)
        service.voice_client = vc
        service.resume()
        vc.resume.assert_called_once()

    def test_is_playing(self, service, mocker):
        vc = make_mock_vc(mocker)
        service.voice_client = vc
        vc.is_playing.return_value = True
        assert service.is_playing() is True

    def test_is_paused(self, service, mocker):
        vc = make_mock_vc(mocker)
        service.voice_client = vc
        vc.is_paused.return_value = True
        assert service.is_paused() is True

    def test_play_delegates(self, service, mocker):
        vc = make_mock_vc(mocker)
        service.voice_client = vc
        source = object()
        callback = lambda e: None
        service.play(source, after=callback)
        vc.play.assert_called_once_with(source, after=callback)

    @pytest.mark.asyncio
    async def test_join_voice_channel_no_voice(self, service, mocker):
        interaction = mocker.Mock()
        interaction.user.voice = None
        result = await service.join_voice_channel(interaction)
        assert result is False

    @pytest.mark.asyncio
    async def test_join_voice_channel_connects(self, service, mocker):
        mock_vc = make_mock_vc(mocker)
        ch = make_mock_channel(mocker)
        ch.connect.return_value = mock_vc
        interaction = mocker.Mock()
        interaction.user.voice.channel = ch
        result = await service.join_voice_channel(interaction)
        assert result is True
        assert service.voice_client is mock_vc
        mock_vc.set_davey.assert_called_once_with(True)

    @pytest.mark.asyncio
    async def test_disconnect_stops_and_disconnects(self, service, mocker):
        mock_vc = make_mock_vc(mocker)
        mock_vc.disconnect = mocker.AsyncMock(return_value=None)
        service.channel = "chan"
        service.voice_client = mock_vc
        await service.disconnect()
        mock_vc.stop.assert_called_once()
        mock_vc.disconnect.assert_called_once()
        assert service.channel is None

    def test_start_recording_delegates(self, service, mocker):
        vc = make_mock_vc(mocker)
        service.voice_client = vc
        sink = object()
        service.start_recording(sink, after=lambda e: None)
        vc.listen.assert_called_once()

    def test_stop_recording_delegates(self, service, mocker):
        vc = make_mock_vc(mocker)
        service.voice_client = vc
        service.stop_recording()
        vc.stop_listening.assert_called_once()

    def test_is_recording_delegates(self, service, mocker):
        vc = make_mock_vc(mocker)
        service.voice_client = vc
        vc.is_listening.return_value = True
        assert service.is_recording() is True

    @pytest.mark.asyncio
    async def test_move_to_channel(self, service, mocker):
        old_vc = make_mock_vc(mocker)
        old_vc.disconnect = mocker.AsyncMock(return_value=None)
        new_vc = make_mock_vc(mocker)
        new_ch = make_mock_channel(mocker)
        new_ch.connect.return_value = new_vc
        service.voice_client = old_vc
        service.channel = "old"
        interaction = mocker.Mock()
        interaction.user.voice.channel = new_ch
        await service.move_to_channel(interaction)
        old_vc.stop.assert_called_once()
        old_vc.disconnect.assert_called_once()
        assert service.voice_client is new_vc
        new_vc.set_davey.assert_called_once_with(True)
