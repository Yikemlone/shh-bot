from discord import app_commands, Interaction
from discord.ext import commands
from services.api.jisho import JapaneseConnection
from core.logger import logging, SHH_BOT

logger = logging.getLogger(SHH_BOT)


class Japanese(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


    @app_commands.command(name="translate", description="This will translate a word to Japanese.")
    @app_commands.describe(message="The word you want to translate.")
    async def translate(self, interaction : Interaction, message : str):
        logger.info(f"Translaiting: {message}")
        translation = await JapaneseConnection.get_data(message)
        await interaction.response.send_message(translation)


async def setup(bot):
    await bot.add_cog(Japanese(bot))
