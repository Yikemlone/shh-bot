from unittest.mock import MagicMock, AsyncMock, patch
import pytest
from services.music.song import SongService


class TestSongService:
    def test_init(self):
        s = SongService()
        assert s.FFMPEG_EXE_PATH == "ffmpeg"

    def test_get_song_source_returns_none_initially(self):
        assert SongService().get_song_source() is None

    def test_prep_song_source(self):
        mock_ydl = MagicMock()
        mock_ydl.__enter__.return_value.extract_info.return_value = {"url": "http://stream"}
        with patch("yt_dlp.YoutubeDL", return_value=mock_ydl):
            s = SongService()
            s.prep_soung_source("https://youtube.com/watch?v=test")
            assert s.song_source is not None

    @pytest.mark.asyncio
    async def test_get_song_details_url(self):
        s = SongService()
        result = await s.get_song_details("https://youtube.com/watch?v=test")
        assert result["name"] == "Unknown"
