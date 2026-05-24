import os
from pathlib import Path
import yt_dlp as youtube_dl
from discord import FFmpegPCMAudio
from services.api.spotify import SpotifyConnection
from services.api.youtube import YouTubeConnection
from core.logger import logging, SHH_BOT

BASE_DIR = Path(__file__).resolve().parent.parent.parent
logger = logging.getLogger(SHH_BOT)


class SongService():

    def __init__(self):
        self.FFMPEG_OPTIONS: dict = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
        self.YT_DL_OPTIONS: dict = {'format': 'bestaudio[ext=m4a]/bestaudio', 'noplaylist': True, 'quiet': True, 'js_runtimes': {'node': {}}}
        self.FFMPEG_EXE_PATH: str = "ffmpeg"
        self.song_source: FFmpegPCMAudio = None

    def get_song_source(self) -> FFmpegPCMAudio:
        return self.song_source

    def prep_soung_source(self, song_url):
        try:
            with youtube_dl.YoutubeDL(self.YT_DL_OPTIONS) as ydl:
                song_information = ydl.extract_info(song_url, download=False)
                song_url = song_information["url"]
                self.song_source = FFmpegPCMAudio(song_url, **self.FFMPEG_OPTIONS, executable=self.FFMPEG_EXE_PATH)
        except Exception as ex:
            logger.error(f"Error in prep_soung_source: {ex}")

    async def get_song_details(self, song_name) -> dict:
        if "http" in song_name:
            return {"URL": song_name, "name": "Unknown", "song": "Unknown"}

        use_spotify = os.getenv("USE_SPOTIFY", "true").lower() == "true"

        if use_spotify:
            song_details = await SpotifyConnection.get_data(song_name)
            if song_details:
                url = await self._get_link(song_name)
                if url:
                    return {"URL": url, "name": song_details["name"], "song": song_details["song"]}
            logger.warning(f"Spotify failed for {song_name}, falling back to yt-dlp.")

        return await self._search_youtube(song_name)

    async def _search_youtube(self, query: str) -> dict | None:
        try:
            with youtube_dl.YoutubeDL({
                'quiet': True,
                'default_search': 'ytsearch',
                'max_downloads': 1,
                'noplaylist': True,
                'js_runtimes': {'node': {}},
            }) as ydl:
                info = ydl.extract_info(f"ytsearch:{query}", download=False)
                video = info['entries'][0]
                return {
                    "URL": video['webpage_url'],
                    "name": video.get('uploader', 'Unknown'),
                    "song": video.get('title', 'Unknown'),
                }
        except Exception as ex:
            logger.error(f"yt-dlp search failed for {query}: {ex}")
            return None

    async def _get_link(self, name: str) -> str | None:
        link = await YouTubeConnection.get_data(name)
        if link is None:
            logger.error(f"Error getting link for {name}")
        return link