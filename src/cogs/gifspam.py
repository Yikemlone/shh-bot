import random
from discord import app_commands, Interaction
from discord.ext import commands
from services.api.giphy import GiphyConnection
from core.permissions import user_has_role, is_moderator
from core.logger import logging, SHH_BOT

logger = logging.getLogger(SHH_BOT)


class GifSpam(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.gif_on = False
        self.gif_role = "GIFFER"


    @commands.Cog.listener()
    async def on_message(self, message):
        """Will check if the bot should post gifs."""
        if message.author.bot:
            return

        if self.gif_on:
            await self.post_gif(message)


    @app_commands.command(name="gif_time", description="This toggles the bot on and off from posting gifs.")
    async def gif(self, interaction: Interaction):
        """Toggles the bot on and off from posting gifs."""

        if not user_has_role(interaction, self.gif_role) and not is_moderator(interaction.user):
            await interaction.response.send_message(f"{interaction.user.mention} you don't have the permissions for this.", ephemeral=True)
            return
            
        self.gif_on = not self.gif_on
        await interaction.response.send_message(f"{'✅' if self.gif_on else '❌'} Gif spam is now {'on' if self.gif_on else 'off'}.")


    async def post_gif(self, message):
        """Will post a gif in the server"""
        ctx = await self.bot.get_context(message)
        word = message.content
        gif_data = await GiphyConnection.get_data(word)

        if len(gif_data) == 0:
            return

        await ctx.send(random.choice(gif_data)["url"])


async def setup(bot):
    await bot.add_cog(GifSpam(bot))