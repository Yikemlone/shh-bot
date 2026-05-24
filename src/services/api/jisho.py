import aiohttp
from util.apiconnection.apiconnection import APIConnection
from urllib import parse
from util.logger import logging, SHH_BOT

logger = logging.getLogger(SHH_BOT)


class JapaneseConnection(APIConnection):

    @staticmethod
    async def get_data(word: str):
        try:
            data = parse.quote(data)
            logger.info(f"Getting tranlation for {word}")
            URL = f"https://jisho.org/api/v1/search/words?keyword={word}"

            async with aiohttp.ClientSession() as session:
                async with session.get(URL) as response:
                    content = await response.json()

            if content["meta"]["status"] != 200:
                return "Sorry, there was an issue getting the translation. Try again later"

            output = f"Kanji: {content['data'][0]['japanese'][0].get('word', 'No Kanji')}\t" \
                     f"Hiragana: {content['data'][0]['japanese'][0].get('reading', 'No Hiragana')}"

            return output

        except Exception as ex:
            logger.error(f"Error fetching data: {ex}")
            return "Error: Could not communicate with API"