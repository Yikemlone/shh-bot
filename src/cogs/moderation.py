from discord import app_commands, Interaction
from discord.ext import commands
from core.logger import logging, SHH_BOT

logger = logging.getLogger(SHH_BOT)


class Moderation(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


    @app_commands.command(name="clear", description="Clears the chat")
    @app_commands.describe(amount="The amount of messages to clear")
    @app_commands.guild_only()
    async def clear(self, interaction : Interaction, amount : int = 6): 
        await interaction.channel.purge(limit=amount)
        await interaction.response.send_message(f"✅ Cleared {amount} messages.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Moderation(bot))
