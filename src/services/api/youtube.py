import os 
from googleapiclient.discovery import build
from urllib import parse
from util.apiconnection.apiconnection import APIConnection
from util.logger import logging, SHH_BOT

logger = logging.getLogger(SHH_BOT)

class YouTubeConnection(APIConnection):

    @staticmethod
    async def get_data(data):
        try:
            data = parse.quote(data)
            YOUTUBE = build("youtube", "v3", developerKey=os.getenv("YOUTUBE_API_KEY"))

            request = YOUTUBE.search().list(
                part="snippet",
                maxResults=1,
                q=f"{data}"
            )

            response = request.execute()
            video_id = response["items"][0]["id"]["videoId"]

            return f"https://www.youtube.com/watch?v={video_id}"

        except IndexError:
            logger.warning("No video found.")
            return "https://www.youtube.com/watch?v=dQw4w9WgXcQ&ab_channel=RickAstley"
        except Exception as ex:
            logger.error(ex)
