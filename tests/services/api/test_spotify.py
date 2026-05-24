import aioresponses
import pytest
from services.api.spotify import SpotifyConnection


@pytest.fixture(autouse=True)
def mock_env(mocker):
    mocker.patch.dict("os.environ", {
        "SPOTIFY_ID": "test_id",
        "SPOTIFY_SECRET": "test_secret",
        "SPOTIFY_TOKEN": "stored_token",
    })
    SpotifyConnection._token = "valid_token"
    SpotifyConnection._token_expires_at = 9999999999


SEARCH_URL = "https://api.spotify.com/v1/search?q=test+song&type=track&limit=1"
SEARCH_URL_UNKNOWN = "https://api.spotify.com/v1/search?q=unknown&type=track&limit=1"
SEARCH_URL_SIMPLE = "https://api.spotify.com/v1/search?q=test&type=track&limit=1"
TOKEN_URL = "https://accounts.spotify.com/api/token"


class TestSpotifyConnection:
    @pytest.mark.asyncio
    async def test_get_data_returns_song_details(self):
        with aioresponses.aioresponses() as m:
            m.get(
                SEARCH_URL,
                payload={
                    "tracks": {"items": [{"artists": [{"name": "Artist"}], "name": "Song"}]}
                },
            )
            result = await SpotifyConnection.get_data("test song")
            assert result == {"name": "Artist", "song": "Song"}

    @pytest.mark.asyncio
    async def test_get_data_no_results(self):
        with aioresponses.aioresponses() as m:
            m.get(SEARCH_URL_UNKNOWN, payload={"tracks": {"items": []}})
            result = await SpotifyConnection.get_data("unknown")
            assert result is None

    @pytest.mark.asyncio
    async def test_get_data_token_expired_retries(self):
        SpotifyConnection._token_expires_at = 0
        with aioresponses.aioresponses() as m:
            m.post(TOKEN_URL, payload={"access_token": "refreshed", "expires_in": 3600})
            m.get(SEARCH_URL_SIMPLE, status=401)
            m.get(
                SEARCH_URL_SIMPLE,
                payload={"tracks": {"items": [{"artists": [{"name": "A"}], "name": "B"}]}},
            )
            result = await SpotifyConnection.get_data("test")
            assert result == {"name": "A", "song": "B"}

    @pytest.mark.asyncio
    async def test_get_data_rate_limited(self):
        with aioresponses.aioresponses() as m:
            m.get(SEARCH_URL_SIMPLE, status=429, headers={"Retry-After": "0"})
            m.get(
                SEARCH_URL_SIMPLE,
                payload={"tracks": {"items": [{"artists": [{"name": "A"}], "name": "B"}]}},
            )
            result = await SpotifyConnection.get_data("test")
            assert result == {"name": "A", "song": "B"}

    @pytest.mark.asyncio
    async def test_get_data_api_error(self):
        with aioresponses.aioresponses() as m:
            m.get(SEARCH_URL_SIMPLE, status=500)
            result = await SpotifyConnection.get_data("test")
            assert result is None

    @pytest.mark.asyncio
    async def test_get_data_request_exception(self):
        with aioresponses.aioresponses() as m:
            m.get(SEARCH_URL_SIMPLE, exception=ConnectionError("timeout"))
            result = await SpotifyConnection.get_data("test")
            assert result is None

    @pytest.mark.asyncio
    async def test_no_valid_token_returns_none(self):
        SpotifyConnection._token_expires_at = 0
        with aioresponses.aioresponses() as m:
            m.post(TOKEN_URL, status=400, payload={"error": "invalid_client"})
            result = await SpotifyConnection.get_data("test")
            assert result is None

    @pytest.mark.asyncio
    async def test_stored_token_used_when_refresh_fails(self):
        SpotifyConnection._token_expires_at = 0
        with aioresponses.aioresponses() as m:
            m.post(TOKEN_URL, status=400, payload={"error": "invalid_client"})
            m.get(SEARCH_URL_SIMPLE, payload={"tracks": {"items": [{"artists": [{"name": "A"}], "name": "B"}]}})
            result = await SpotifyConnection.get_data("test")
            assert result == {"name": "A", "song": "B"}
