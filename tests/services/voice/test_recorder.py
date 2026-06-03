import wave
from pathlib import Path
from unittest.mock import patch
from services.voice.recorder import SSRCWaveSink, CHANNELS, SAMPLE_WIDTH, SAMPLING_RATE, BYTES_PER_FRAME


def make_voice_data(mocker, ssrc=12345, opus=b"\x00" * 40, timestamp=0):
    data = mocker.Mock()
    data.packet.ssrc = ssrc
    data.packet.timestamp = timestamp
    data.opus = opus
    return data


class TestSSRCWaveSink:
    def test_wants_opus_returns_true(self, tmp_path):
        sink = SSRCWaveSink(tmp_path, "test")
        assert sink.wants_opus()

    def test_creates_wav_file_on_new_ssrc(self, mocker, tmp_path):
        sink = SSRCWaveSink(tmp_path, "test")
        data = make_voice_data(mocker)
        sink.write(None, data)
        assert 12345 in sink.ssrcs
        expected = tmp_path / "ssrc_12345_test.wav"
        assert expected.exists()

    def test_writes_pcm_data(self, mocker, tmp_path):
        with patch("services.voice.recorder.opuslib.Decoder") as mock_decoder_cls:
            mock_decoder = mocker.Mock()
            mock_decoder.decode.return_value = b"\x01\x00" * (BYTES_PER_FRAME // 2)
            mock_decoder_cls.return_value = mock_decoder

            sink = SSRCWaveSink(tmp_path, "test")
            data = make_voice_data(mocker)
            sink.write(None, data)
            path = sink.get_path(12345)
            assert path is not None
            with wave.open(str(path), "rb") as wf:
                assert wf.getnchannels() == CHANNELS
                assert wf.getsampwidth() == SAMPLE_WIDTH
                assert wf.getframerate() == SAMPLING_RATE
                frames = wf.readframes(wf.getnframes())
                assert len(frames) == BYTES_PER_FRAME
            mock_decoder.decode.assert_called_once_with(data.opus, 960)

    def test_multiple_ssrcs_create_separate_files(self, mocker, tmp_path):
        with patch("services.voice.recorder.opuslib.Decoder"):
            sink = SSRCWaveSink(tmp_path, "test")
            sink.write(None, make_voice_data(mocker, ssrc=1))
            sink.write(None, make_voice_data(mocker, ssrc=2))
            assert sink.ssrcs == [1, 2]

    def test_cleanup_closes_and_clears(self, mocker, tmp_path):
        with patch("services.voice.recorder.opuslib.Decoder"):
            sink = SSRCWaveSink(tmp_path, "test")
            sink.write(None, make_voice_data(mocker))
            sink.cleanup()
            assert sink.ssrcs == []

    def test_get_path_returns_path_and_removes(self, mocker, tmp_path):
        with patch("services.voice.recorder.opuslib.Decoder"):
            sink = SSRCWaveSink(tmp_path, "test")
            sink.write(None, make_voice_data(mocker))
            path = sink.get_path(12345)
            assert path is not None
            assert path.name == "ssrc_12345_test.wav"
            assert 12345 not in sink.ssrcs

    def test_get_path_returns_none_for_missing(self, tmp_path):
        sink = SSRCWaveSink(tmp_path, "test")
        assert sink.get_path(99999) is None

    def test_skips_empty_opus_without_creating_file(self, mocker, tmp_path):
        sink = SSRCWaveSink(tmp_path, "test")
        data = make_voice_data(mocker, opus=b"")
        sink.write(None, data)
        assert sink.ssrcs == []
