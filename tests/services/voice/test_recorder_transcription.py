import asyncio
import struct
import wave
from pathlib import Path
from unittest.mock import AsyncMock
import pytest
from services.voice.recorder import TranscriptionService, CHANNELS, SAMPLE_WIDTH, SAMPLING_RATE


def make_wav(path: Path, duration_frames: int = 48000):
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(SAMPLE_WIDTH)
        wf.setframerate(SAMPLING_RATE)
        frames = struct.pack(f"<{duration_frames * CHANNELS}h", *([100] * duration_frames * CHANNELS))
        wf.writeframes(frames)


def mock_voice_client(mocker):
    vc = mocker.Mock()
    vc.mode = "xsalsa20_poly1305"
    vc.ssrc = 12345
    vc._get_id_from_ssrc.return_value = 67890
    vc.set_davey = mocker.Mock()
    return vc


@pytest.fixture
def service(mocker, tmp_path):
    mocker.patch("services.voice.recorder.WhisperModel.__init__", return_value=None)
    svc = TranscriptionService()
    svc._recordings_dir = tmp_path
    return svc


class TestTranscriptionService:
    def test_init(self, mocker):
        mocker.patch("services.voice.recorder.WhisperModel.__init__", return_value=None)
        svc = TranscriptionService()
        assert svc.is_recording is False
        assert svc._sink is None

    def test_start_sets_up_recording(self, service, mocker):
        vc = mock_voice_client(mocker)
        tc = mocker.Mock()
        loop = asyncio.new_event_loop()
        service.start(vc, tc, loop)
        assert service.is_recording is True
        assert service._sink is not None
        vc.listen.assert_called_once()

    def test_stop_stops_recording(self, service, mocker):
        vc = mock_voice_client(mocker)
        tc = mocker.Mock()
        loop = asyncio.new_event_loop()
        service.start(vc, tc, loop)
        service.stop(vc)
        assert service.is_recording is False
        vc.stop_listening.assert_called_once()

    def test_goofy_name_format(self, service):
        name = service._goofy_name()
        assert any(adj in name for adj in service._adjectives)
        assert any(noun in name for noun in service._nouns)

    def test_is_recording_property(self, service):
        assert service.is_recording is False
        service._recording = True
        assert service.is_recording is True

    def test_analyze_pcm_stereo(self, service, tmp_path):
        wav = tmp_path / "test.wav"
        make_wav(wav, 100)
        service._analyze_pcm(wav, 12345)

    def test_analyze_pcm_short_skips(self, service, tmp_path):
        wav = tmp_path / "short.wav"
        with wave.open(str(wav), "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(SAMPLE_WIDTH)
            wf.setframerate(SAMPLING_RATE)
            wf.writeframes(b"")
        service._analyze_pcm(wav, 12345)

    def test_on_stop_captures_ssrcs(self, service, mocker):
        vc = mock_voice_client(mocker)
        tc = mocker.Mock()
        loop = asyncio.new_event_loop()
        service.start(vc, tc, loop)
        sink = service._sink
        wav = service._recordings_dir / "ssrc_1_test.wav"
        make_wav(wav, 100)
        sink._files[1] = wave.open(str(wav), "rb")
        service._on_stop(None)
        assert not service.is_recording

    @pytest.mark.asyncio
    async def test_transcribe_returns_text(self, service, tmp_path, mocker):
        mock_seg = mocker.Mock()
        mock_seg.start = 0.0
        mock_seg.end = 1.0
        mock_seg.text = "hello world"
        mock_info = mocker.Mock()
        mock_info.language = "en"
        mock_info.language_probability = 0.95
        service._model = mocker.Mock()
        service._model.transcribe.return_value = ([mock_seg], mock_info)
        wav = tmp_path / "test.wav"
        make_wav(wav, 100)
        result = await service._transcribe(wav)
        assert result == "hello world"

    @pytest.mark.asyncio
    async def test_transcribe_returns_none_on_empty(self, service, tmp_path, mocker):
        mock_info = mocker.Mock()
        mock_info.language = "en"
        mock_info.language_probability = 0.95
        service._model = mocker.Mock()
        service._model.transcribe.return_value = ([], mock_info)
        wav = tmp_path / "test.wav"
        make_wav(wav, 100)
        result = await service._transcribe(wav)
        assert result is None

    @pytest.mark.asyncio
    async def test_transcribe_handles_exception(self, service, tmp_path, mocker):
        service._model = mocker.Mock()
        service._model.transcribe.side_effect = RuntimeError("model error")
        wav = tmp_path / "test.wav"
        make_wav(wav, 100)
        result = await service._transcribe(wav)
        assert result is None

    @pytest.mark.asyncio
    async def test_wav_to_mp3_converts(self, service, tmp_path, mocker):
        mock_proc = mocker.AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))
        mocker.patch("asyncio.create_subprocess_exec", return_value=mock_proc)
        wav = tmp_path / "test.wav"
        mp3 = tmp_path / "test.mp3"
        mp3.write_bytes(b"fake mp3 data")
        make_wav(wav, 100)
        result = await service._wav_to_mp3(wav)
        assert result == mp3

    @pytest.mark.asyncio
    async def test_wav_to_mp3_ffmpeg_fails(self, service, tmp_path, mocker):
        mock_proc = mocker.AsyncMock()
        mock_proc.returncode = 1
        mock_proc.communicate = AsyncMock(return_value=(b"", b"error"))
        mocker.patch("asyncio.create_subprocess_exec", return_value=mock_proc)
        mp3 = tmp_path / "test.mp3"
        mp3.write_bytes(b"fake")
        wav = tmp_path / "test.wav"
        make_wav(wav, 100)
        result = await service._wav_to_mp3(wav)
        assert result is None

    @pytest.mark.asyncio
    async def test_wav_to_mp3_ffmpeg_not_found(self, service, tmp_path, mocker):
        mocker.patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError)
        wav = tmp_path / "test.wav"
        make_wav(wav, 100)
        result = await service._wav_to_mp3(wav)
        assert result is None

    @pytest.mark.asyncio
    async def test_process_no_ssrcs_sends_message(self, service, mocker):
        tc = mocker.Mock()
        tc.send = AsyncMock()
        service._text_channel = tc
        service._sink = mocker.Mock()
        await service._process(None, [], {})
        tc.send.assert_called_once_with("No speech detected during the recording session.")

    @pytest.mark.asyncio
    async def test_process_no_text_channel(self, service):
        service._text_channel = None
        await service._process(None, [1], {1: None})

    @pytest.mark.asyncio
    async def test_process_full_flow(self, service, tmp_path, mocker):
        wav = tmp_path / "ssrc_1_test.wav"
        make_wav(wav, 100)
        mp3 = tmp_path / "ssrc_1_test.mp3"
        mp3.write_bytes(b"fake mp3")
        mock_proc = mocker.AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))
        mocker.patch("asyncio.create_subprocess_exec", return_value=mock_proc)

        mock_msg = mocker.Mock()
        mock_msg.create_thread = AsyncMock()
        tc = mocker.Mock()
        tc.send = AsyncMock(return_value=mock_msg)
        tc.guild.get_member.return_value = None

        mock_seg = mocker.Mock()
        mock_seg.start = 0.0
        mock_seg.end = 1.0
        mock_seg.text = "hello"
        mock_info = mocker.Mock()
        mock_info.language = "en"
        mock_info.language_probability = 0.95
        service._model = mocker.Mock()
        service._model.transcribe.return_value = ([mock_seg], mock_info)

        vc = mock_voice_client(mocker)
        service._voice_client = vc
        service._text_channel = tc
        service._sink = mocker.Mock()

        await service._process(None, [1], {1: wav})
        tc.send.assert_called_once()
        mock_msg.create_thread.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_process_with_error_logs(self, service, mocker):
        tc = mocker.Mock()
        tc.send = AsyncMock()
        service._text_channel = tc
        service._sink = mocker.MagicMock()
        await service._process(ValueError("test error"), [], {})
        tc.send.assert_called_once()
