import wave
from pathlib import Path
from unittest.mock import MagicMock
from services.voice.recorder import SSRCWaveSink, CHANNELS, SAMPLE_WIDTH, SAMPLING_RATE


def make_voice_data(mocker, ssrc=12345, pcm=b"\x00\x00\x00\x00\x00\x00\x00\x00"):
    data = mocker.Mock()
    data.packet.ssrc = ssrc
    data.packet.timestamp = 0
    data.pcm = pcm
    return data


class TestSSRCWaveSink:
    def test_wants_opus_returns_false(self, tmp_path):
        sink = SSRCWaveSink(tmp_path, "test")
        assert not sink.wants_opus()

    def test_creates_wav_file_on_new_ssrc(self, mocker, tmp_path):
        sink = SSRCWaveSink(tmp_path, "test")
        data = make_voice_data(mocker)
        sink.write(None, data)
        assert 12345 in sink.ssrcs
        expected = tmp_path / "ssrc_12345_test.wav"
        assert expected.exists()

    def test_writes_pcm_data(self, mocker, tmp_path):
        sink = SSRCWaveSink(tmp_path, "test")
        pcm = b"\x01\x00" * 960 * 2 * 2
        data = make_voice_data(mocker, pcm=pcm)
        sink.write(None, data)
        path = sink.get_path(12345)
        assert path is not None
        with wave.open(str(path), "rb") as wf:
            assert wf.getnchannels() == CHANNELS
            assert wf.getsampwidth() == SAMPLE_WIDTH
            assert wf.getframerate() == SAMPLING_RATE
            frames = wf.readframes(wf.getnframes())
            assert frames == pcm

    def test_multiple_ssrcs_create_separate_files(self, mocker, tmp_path):
        sink = SSRCWaveSink(tmp_path, "test")
        sink.write(None, make_voice_data(mocker, ssrc=1))
        sink.write(None, make_voice_data(mocker, ssrc=2))
        assert sink.ssrcs == [1, 2]

    def test_cleanup_closes_and_clears(self, mocker, tmp_path):
        sink = SSRCWaveSink(tmp_path, "test")
        sink.write(None, make_voice_data(mocker))
        sink.cleanup()
        assert sink.ssrcs == []

    def test_get_path_returns_path_and_removes(self, mocker, tmp_path):
        sink = SSRCWaveSink(tmp_path, "test")
        sink.write(None, make_voice_data(mocker))
        path = sink.get_path(12345)
        assert path is not None
        assert path.name == "ssrc_12345_test.wav"
        assert 12345 not in sink.ssrcs

    def test_get_path_returns_none_for_missing(self, tmp_path):
        sink = SSRCWaveSink(tmp_path, "test")
        assert sink.get_path(99999) is None
