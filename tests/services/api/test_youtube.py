import pytest
from services.api.youtube import YouTubeConnection


class TestYouTubeConnection:
    @pytest.mark.asyncio
    async def test_get_data_returns_url(self, mocker):
        mock_build = mocker.patch("services.api.youtube.build")
        mock_search = mock_build.return_value.search
        mock_list = mock_search.return_value.list
        mock_execute = mock_list.return_value.execute
        mock_execute.return_value = {
            "items": [{"id": {"videoId": "abc123"}}]
        }
        result = await YouTubeConnection.get_data("test song")
        assert "abc123" in result

    @pytest.mark.asyncio
    async def test_get_data_index_error_returns_rickroll(self, mocker):
        mock_build = mocker.patch("services.api.youtube.build")
        mock_build.return_value.search.return_value.list.return_value.execute.return_value = {"items": []}
        result = await YouTubeConnection.get_data("nothing")
        assert "dQw4w9WgXcQ" in result

    @pytest.mark.asyncio
    async def test_get_data_handles_exception(self, mocker):
        mocker.patch("services.api.youtube.build", side_effect=RuntimeError("API error"))
        result = await YouTubeConnection.get_data("test")
        assert result is None
