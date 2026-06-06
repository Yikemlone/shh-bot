import asyncio
import struct
import wave
from pathlib import Path
from unittest.mock import AsyncMock
import pytest
from services.voice.recorder import TranscriptionService, CHANNELS, SAMPLE_WIDTH, SAMPLING_RATE, DISCORD_FILE_LIMIT


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

    def test_on_stop_captures_ssrcs(self, service, mocker):
        vc = mock_voice_client(mocker)
        tc = mocker.Mock()
        loop = asyncio.new_event_loop()
        service.start(vc, tc, loop)
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

    def test_transcribe_sync_returns_text(self, service, mocker):
        seg = mocker.Mock()
        seg.text = "hello world"
        info = mocker.Mock()
        info.language = "en"
        service._model = mocker.Mock()
        service._model.transcribe.return_value = ([seg], info)
        result, info_out = service._transcribe_sync("fake.wav")
        assert result == "hello world"
        assert info_out.language == "en"

    def test_transcribe_sync_returns_empty_on_empty(self, service, mocker):
        info = mocker.Mock()
        info.language = "en"
        service._model = mocker.Mock()
        service._model.transcribe.return_value = ([], info)
        result, _ = service._transcribe_sync("fake.wav")
        assert result == ""  # _transcribe_sync returns ""; _transcribe converts to None

    def test_transcribe_sync_joins_multiple_segments(self, service, mocker):
        seg1 = mocker.Mock(text="hello")
        seg2 = mocker.Mock(text="world")
        info = mocker.Mock()
        service._model = mocker.Mock()
        service._model.transcribe.return_value = ([seg1, seg2], info)
        result, _ = service._transcribe_sync("fake.wav")
        assert result == "hello world"

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
    async def test_wav_to_mp3_custom_bitrate(self, service, tmp_path, mocker):
        mock_proc = mocker.AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))
        exec_mock = mocker.patch("asyncio.create_subprocess_exec", return_value=mock_proc)
        wav = tmp_path / "test.wav"
        mp3 = tmp_path / "test.mp3"
        mp3.write_bytes(b"fake mp3")
        make_wav(wav, 100)
        result = await service._wav_to_mp3(wav, bitrate='32k')
        assert result == mp3
        # Verify ffmpeg was called with the custom bitrate
        call_args = exec_mock.call_args[0]
        assert '-b:a' in call_args
        bitrate_idx = call_args.index('-b:a') + 1
        assert call_args[bitrate_idx] == '32k'

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
        mocker.patch.object(service, "_enhance_audio", return_value=None)
        wav = tmp_path / "ssrc_1_test.wav"
        make_wav(wav, 100)
        mp3 = tmp_path / "ssrc_1_test.mp3"
        mp3.write_bytes(b"fake mp3")
        mock_proc = mocker.AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))
        mocker.patch("asyncio.create_subprocess_exec", return_value=mock_proc)

        mock_thread = mocker.AsyncMock()
        mock_msg = mocker.Mock()
        mock_msg.create_thread = AsyncMock(return_value=mock_thread)
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
        assert mock_thread.send.await_count >= 1
        # WAV should NOT exist after successful upload (cleaned up)
        assert not wav.exists()

    @pytest.mark.asyncio
    async def test_process_preserves_file_on_upload_failure(self, service, tmp_path, mocker):
        mocker.patch.object(service, "_enhance_audio", return_value=None)
        mocker.patch.object(service, "_extract_and_store_tasks", return_value=None)
        wav = tmp_path / "ssrc_1_test.wav"
        make_wav(wav, 100)
        mp3 = tmp_path / "ssrc_1_test.mp3"
        mp3.write_bytes(b"fake mp3")
        mock_proc = mocker.AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))
        mocker.patch("asyncio.create_subprocess_exec", return_value=mock_proc)

        mock_thread = mocker.AsyncMock()
        mock_thread.send = AsyncMock(side_effect=RuntimeError("upload failed"))
        mock_msg = mocker.Mock()
        mock_msg.create_thread = AsyncMock(return_value=mock_thread)
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
        # Files should still exist after failed upload
        assert mp3.exists()
        assert wav.exists()

    def test_split_at_word_returns_full_text_when_under_limit(self, service):
        chunk, rest = service._split_at_word("hello world", 100)
        assert chunk == "hello world"
        assert rest == ""

    def test_split_at_word_splits_at_space(self, service):
        chunk, rest = service._split_at_word("hello world foo bar", 12)
        assert chunk == "hello world"
        assert rest == "foo bar"

    def test_split_at_word_hard_cuts_when_no_space(self, service):
        chunk, rest = service._split_at_word("abcdefghij", 5)
        assert chunk == "abcde"
        assert rest == "fghij"

    def test_split_at_word_skips_leading_space_on_rest(self, service):
        chunk, rest = service._split_at_word("one two three four", 8)
        assert chunk == "one two"
        assert rest == "three four"

    def test_split_content_short_returns_single_message(self, service):
        messages = service._split_content("**user**: ", "hello world")
        assert messages == ["**user**: hello world"]

    def test_split_content_long_splits_into_multiple(self, service):
        text = "word " * 500  # ~2500 chars
        prefix = "**<@1234>**: "
        messages = service._split_content(prefix, text)
        assert len(messages) > 1
        assert len(messages[0]) <= 1900
        assert all(len(m) <= 2000 for m in messages)

    def test_split_content_no_space_long_word_hard_cuts(self, service):
        text = "a" * 3000
        prefix = "**u**: "
        messages = service._split_content(prefix, text)
        assert len(messages) > 1
        assert len(messages[0]) <= 1900
        assert all(len(m) <= 2000 for m in messages)

    def test_split_content_empty_text_returns_no_speech(self, service):
        messages = service._split_content("**u**: ", "")
        assert "*[no speech detected]*" in messages[0]

    @pytest.mark.asyncio
    async def test_process_sends_multiple_messages_for_long_transcript(self, service, tmp_path, mocker):
        mocker.patch.object(service, "_enhance_audio", return_value=None)
        wav = tmp_path / "ssrc_1_test.wav"
        make_wav(wav, 100)
        mp3 = tmp_path / "ssrc_1_test.mp3"
        mp3.write_bytes(b"fake mp3")
        mock_proc = mocker.AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))
        mocker.patch("asyncio.create_subprocess_exec", return_value=mock_proc)

        mock_thread = mocker.AsyncMock()
        mock_msg = mocker.Mock()
        mock_msg.create_thread = AsyncMock(return_value=mock_thread)
        tc = mocker.Mock()
        tc.send = AsyncMock(return_value=mock_msg)
        tc.guild.get_member.return_value = None

        long_text = "word " * 500  # ~2500 chars
        seg = mocker.Mock(text=long_text)
        info = mocker.Mock()
        info.language = "en"
        info.language_probability = 0.95
        service._model = mocker.Mock()
        service._model.transcribe.return_value = ([seg], info)

        vc = mock_voice_client(mocker)
        service._voice_client = vc
        service._text_channel = tc
        service._sink = mocker.Mock()

        await service._process(None, [1], {1: wav})
        # First call sends with file, remaining calls send text-only
        assert mock_thread.send.await_count > 1
        first_call = mock_thread.send.await_args_list[0]
        assert len(first_call[0][0]) <= 1900
        # File is in the first send only
        assert "file" in first_call.kwargs
        for call in mock_thread.send.await_args_list[1:]:
            assert "file" not in call.kwargs

    @pytest.mark.asyncio
    async def test_select_upload_file_uses_mp3_when_under_limit(self, service, tmp_path):
        wav = tmp_path / "test.wav"
        mp3 = tmp_path / "test.mp3"
        make_wav(wav, 100)
        mp3.write_bytes(b"x" * 1024)  # 1KB, well under limit
        result = await service._select_upload_file(wav, mp3)
        assert result == mp3

    @pytest.mark.asyncio
    async def test_select_upload_file_falls_back_to_wav_when_mp3_missing(self, service, mocker, tmp_path):
        wav = tmp_path / "test.wav"
        make_wav(wav, 100)
        mock = AsyncMock(return_value=None)
        mocker.patch.object(service, "_wav_to_mp3", mock)
        result = await service._select_upload_file(wav, None)
        assert result == wav

    @pytest.mark.asyncio
    async def test_process_no_results_sends_message(self, service, mocker):
        tc = mocker.Mock()
        tc.send = AsyncMock()
        service._text_channel = tc
        service._sink = mocker.Mock()
        await service._process(None, [1], {1: None})
        tc.send.assert_called_once_with("No audio files found to process.")

    @pytest.mark.asyncio
    async def test_process_with_error_logs(self, service, mocker):
        tc = mocker.Mock()
        tc.send = AsyncMock()
        service._text_channel = tc
        service._sink = mocker.MagicMock()
        await service._process(ValueError("test error"), [], {})
        tc.send.assert_called_once()
