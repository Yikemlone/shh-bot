import os
import time
import asyncio
import urllib.parse
import aiohttp
import dotenv
from pathlib import Path
from services.api.base import APIConnection
from core.logger import logging, SHH_BOT

logger = logging.getLogger(SHH_BOT)

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class SpotifyConnection(APIConnection):
    _token: str | None = None
    _token_expires_at: float = 0
    _session: aiohttp.ClientSession | None = None

    @classmethod
    async def _get_session(cls) -> aiohttp.ClientSession:
        if cls._session is None or cls._session.closed:
            cls._session = aiohttp.ClientSession()
        return cls._session

    @classmethod
    async def _get_valid_token(cls) -> str | None:
        if cls._token and time.time() < cls._token_expires_at - 60:
            return cls._token
        token = await cls._refresh_token()
        if token:
            return token
        stored = os.getenv("SPOTIFY_TOKEN")
        if stored:
            logger.warning("Token refresh failed, falling back to stored token.")
            return stored
        return None

    @classmethod
    async def _refresh_token(cls) -> str | None:
        session = await cls._get_session()
        body = {"grant_type": "client_credentials"}
        try:
            async with session.post(
                "https://accounts.spotify.com/api/token",
                data=body,
                auth=aiohttp.BasicAuth(
                    os.getenv("SPOTIFY_ID"), os.getenv("SPOTIFY_SECRET")
                ),
            ) as resp:
                data = await resp.json()
                if resp.status != 200:
                    logger.error(f"Token refresh failed: {data}")
                    return None
                cls._token = data["access_token"]
                cls._token_expires_at = time.time() + data["expires_in"]
                os.environ["SPOTIFY_TOKEN"] = cls._token
                dotenv.set_key(
                    str(BASE_DIR / ".env"), "SPOTIFY_TOKEN", cls._token
                )
                return cls._token
        except Exception as ex:
            logger.error(f"Token refresh error: {ex}")
            return None

    @classmethod
    async def get_data(cls, data: str, _retries: int = 2):
        """Returns dict with artist name and track name, or None."""
        token = await cls._get_valid_token()
        if not token:
            logger.error("No valid Spotify token available.")
            return None

        session = await cls._get_session()
        params = urllib.parse.urlencode({
            "q": data,
            "type": "track",
            "limit": 1,
        })

        try:
            async with session.get(
                f"https://api.spotify.com/v1/search?{params}",
                headers={"Authorization": f"Bearer {token}"},
            ) as resp:
                if resp.status == 401 and _retries > 0:
                    cls._token = None
                    logger.warning("Token expired, refreshing.")
                    return await cls.get_data(data, _retries - 1)

                if resp.status == 429 and _retries > 0:
                    retry_after = int(resp.headers.get("Retry-After", 5))
                    logger.warning(f"Rate limited, retrying in {retry_after}s.")
                    await asyncio.sleep(retry_after)
                    return await cls.get_data(data, _retries - 1)

                if resp.status != 200:
                    logger.error(f"Spotify API returned {resp.status}")
                    return None

                response_data = await resp.json()

        except Exception as ex:
            logger.error(f"Spotify API request error: {ex}")
            return None

        items = response_data.get("tracks", {}).get("items", [])
        items = [i for i in items if i is not None]
        if not items:
            logger.error(f"No results found for query. Response keys: {list(response_data.keys())}")
            return None

        return {
            "name": items[0]["artists"][0]["name"],
            "song": items[0]["name"],
        }

    @staticmethod
    def get_random_song(artist):
        pass
