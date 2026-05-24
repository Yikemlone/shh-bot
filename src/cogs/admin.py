from discord import Interaction
import os
from discord import app_commands
from discord.ext import commands
from util.util import is_guild_owner
from util.logger import logging, SHH_BOT

logger = logging.getLogger(SHH_BOT)


class Cog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot : commands.bot = bot


    async def cog_autocomplete(self, interaction: Interaction, current: str) -> list[app_commands.Choice[str]]:
        """Autocomplete function for cogs."""
        choices = [
            app_commands.Choice(name=cog[:-3], value=f"cogs.{cog[:-3]}")
            for cog in os.listdir("src/cogs") if cog.endswith(".py") and cog != "__init__.py" and current.lower() in cog.lower()
        ]

        return choices[:25]
    

    @app_commands.command(name="load", description="Loads the COGS into the bot") 
    @app_commands.autocomplete(cog=cog_autocomplete)
    async def load(self, interaction : Interaction, cog : str) -> None:
        """Loads a cog into the bot"""
        if not is_guild_owner(interaction):
            await interaction.response.send_message(f"{interaction.user.mention} you are not the server owner.", ephemeral=True)
            return
        
        if self.check_if_cog_is_loaded(cog):
            await interaction.response.send_message(f"The cog **{cog.replace("cogs.", "")}** is already loaded.", ephemeral=True)
            return

        await self.bot.load_extension(cog)
        await interaction.response.send_message(f"Loaded **{cog.replace("cogs.", "")}**")


    @app_commands.command(name="unload", description="Unloads the COGS from the bot")
    @app_commands.autocomplete(cog=cog_autocomplete) 
    async def unload(self, interaction : Interaction, cog : str) -> None:
        """Unloads a cog from the bot"""
        if not is_guild_owner(interaction):
            await interaction.response.send_message(f"{interaction.user.mention} you are not the server owner.", ephemeral=True)
            return
        
        if not self.check_if_cog_is_loaded(cog):
            await interaction.response.send_message(f"The cog **{cog.replace("cogs.", "")}** is already unloaded.", ephemeral=True)
            return
        
        await self.bot.unload_extension(cog)
        await interaction.response.send_message(f"Unloaded **{cog.replace("cogs.", "")}**.", ephemeral=True)


    @app_commands.command(name="reload", description="Reloads the COGS into the bot") 
    @app_commands.autocomplete(cog=cog_autocomplete)
    async def reload(self, interaction : Interaction, cog : str) -> None:
        """Reloads a cog from the bot"""
        if not is_guild_owner(interaction):
            await interaction.response.send_message(f"{interaction.user.mention} you are not the server owner.", ephemeral=True)
            return
        
        if not self.check_if_cog_is_loaded(cog):
            await self.bot.load_extension(f"{cog}")
            return

        await self.bot.unload_extension(f"{cog}")
        await self.bot.load_extension(f"{cog}")
        await interaction.response.send_message(f"Reloaded **{cog.replace("cogs.", "")}**.", ephemeral=True)


    def check_if_cog_is_loaded(self, cog: str) -> bool:
        return cog in list(self.bot.extensions.keys())
    

async def setup(bot: commands.Bot):
    await bot.add_cog(Cog(bot))
