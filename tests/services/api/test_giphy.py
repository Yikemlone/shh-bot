import aioresponses
import pytest
from services.api.giphy import GiphyConnection


class TestGiphyConnection:
    @pytest.mark.asyncio
    async def test_get_data_returns_gifs(self, mocker):
        mocker.patch.dict("os.environ", {"GIF_API_KEY": "test_key"})
        with aioresponses.aioresponses() as mocked:
            mocked.get(
                "http://api.giphy.com/v1/gifs/search?q=cat&api_key=test_key&limit=20&rating=pg",
                payload={"data": [{"id": "abc"}, {"id": "def"}]},
            )
            result = await GiphyConnection.get_data("cat")
            assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_data_handles_empty(self, mocker):
        mocker.patch.dict("os.environ", {"GIF_API_KEY": "test_key"})
        with aioresponses.aioresponses() as mocked:
            mocked.get(
                "http://api.giphy.com/v1/gifs/search?q=zzz&api_key=test_key&limit=20&rating=pg",
                payload={"data": []},
            )
            result = await GiphyConnection.get_data("zzz")
            assert result == []

    @pytest.mark.asyncio
    async def test_get_data_handles_exception(self, mocker):
        mocker.patch.dict("os.environ", {"GIF_API_KEY": "test_key"})
        with aioresponses.aioresponses() as mocked:
            mocked.get(
                "http://api.giphy.com/v1/gifs/search?q=bad&api_key=test_key&limit=20&rating=pg",
                exception=ConnectionError("fail"),
            )
            result = await GiphyConnection.get_data("bad")
            assert result == []
