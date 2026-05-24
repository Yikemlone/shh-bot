import discord
import datetime
from discord.ext import commands
from core.logger import logging, SHH_BOT

logger = logging.getLogger(SHH_BOT)

# TODO: Review for removal 

class TimeConverter(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        smush_emoji = discord.utils.get(self.bot.emojis, name="smush")

        if self.has_time(message.content):
            await message.add_reaction(smush_emoji)

    @staticmethod
    def has_time(message):
        """Will return true if the message has a valid time."""
        # logger.info(message)
        return False

    async def validate_time(self, message):
        """Will check the if the time in the message is valid."""
        pass

    async def send_user_converted_time(self, user):
        """Will send the user who reacted the time converted to their local time."""
        pass

    async def convert_time(self, time):
        """Returns the time passed in converted to user local time."""


async def setup(bot):
    await bot.add_cog(TimeConverter(bot))
