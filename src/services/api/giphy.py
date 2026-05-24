import os
import aiohttp
import urllib.parse
from util.apiconnection.apiconnection import APIConnection
from urllib import parse
from util.logger import logging, SHH_BOT

logger = logging.getLogger(SHH_BOT)


class GiphyConnection(APIConnection):

    @staticmethod
    async def get_data(data):
        try:
            data = parse.quote(data)
            URL = "http://api.giphy.com/v1/gifs/search?"

            params = urllib.parse.urlencode({
                "q": data,
                "api_key": os.getenv("GIF_API_KEY"),
                "limit": "20",
                "rating": "pg"
            })

            async with aiohttp.ClientSession() as session:
                async with session.get(URL + params) as response:
                    gif = await response.json()

            return gif.get("data", [])  # Return an empty list if no data is found

        except Exception as ex:
            logger.error(f"Error fetching Giphy data: {ex}")
            return []