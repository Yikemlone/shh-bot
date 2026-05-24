import asyncio
import random
import os
from pathlib import Path
from discord import app_commands, Interaction
from discord.ext import commands
from core.permissions import user_has_role
from core.logger import logging, SHH_BOT

logger = logging.getLogger(SHH_BOT)

class BasicCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.resource_path = str(Path(__file__).resolve().parent.parent / "resources")
        self.spam_file_name = "beemovie.txt"
        self._8_ball_file = "8ball-response.txt"
        self.text_files_folder = "text-files"
        self.spammer_role_name = "Spammer"
        self.file = None


    @app_commands.command(name="ping", description="Check the latency of the bot.")
    async def _ping(self, interaction: Interaction):
        await interaction.response.send_message(f"Pong! {round(self.bot.latency * 1000)}ms")


    @app_commands.command(name="8_ball", description="Ask a question and the bot will answer.")
    @app_commands.describe(question="The question you want to ask the bot.")
    async def _8ball(self, interaction: Interaction, question: str):
        """Responds with a random answer from the 8-ball list."""
        try:
            file_path = os.path.join(self.resource_path, self.text_files_folder, self._8_ball_file)
            with open(file_path, "r", encoding="utf-8") as file:
                responses = [line.strip() for line in file if line.strip()]

            if not responses:
                await interaction.response.send_message("❌ Error: No responses found in 8ball file.", ephemeral=True)
                return

            answer = random.choice(responses)
            await interaction.response.send_message(f"🎱 **Question:** {question}\n🔮 **Answer:** {answer}")

        except FileNotFoundError:
            await interaction.response.send_message("Oops, something went wrong, try again later", ephemeral=True)
        except Exception as ex:
            logger.error(f"8-ball command error: {ex}")
            await interaction.response.send_message("Oops, something went wrong, try again later", ephemeral=True)


    @app_commands.command(name="ez", description="This is for a monkey.")
    async def ez(self, interaction: Interaction):
        """Will respond with a message in chat. This is meant for one person only."""
        if interaction.user.global_name != os.getenv('MONKEY'):
            await interaction.response.send_message(f"{interaction.user.mention} you're not a monkey, go away.")
            return

        await interaction.response.send_message("ggez no re, bot :)")


    @app_commands.command(name="spam", description="This will spam the chat with the Bee Movie script.")
    async def spam(self, interaction: Interaction):
        """Spams the chat with the Bee Movie script, if the user has the Spammer role."""
        userHasRole = user_has_role(interaction, self.spammer_role_name)
        await interaction.response.defer()

        if not userHasRole:
            await interaction.followup.send("❌ You do not have the Spammer role!", ephemeral=True)
            return

        try:
            file_path = os.path.join(self.resource_path, self.text_files_folder, self.spam_file_name)
            with open(file_path, "r", encoding="utf-8") as file:
                self.spamming = True 

                for line in file:
                    if not self.spamming: 
                        break

                    if line.strip(): 
                        await asyncio.sleep(1)
                        await interaction.followup.send(line.strip())

        except FileNotFoundError as ex:
            logger.warning(f"Error with file: {ex}")
            await interaction.followup.send("Oops, something went wrong...try again later", ephemeral=True)
        except Exception as ex:
            logger.error(f"Error with file: {ex}")
            await interaction.followup.send(f"Oops, something went wrong...try again later", ephemeral=True)


    @app_commands.command(name="stop_spam", description="This will stop the spam.")
    async def stop_spam(self, interaction: Interaction):
        """Stops the spamming process."""
        
        if hasattr(self, "spamming") and self.spamming:
            self.spamming = False  # Set the flag to stop spamming
            await interaction.response.send_message(f"{interaction.user.mention} stopped the spamming.")
        else:
            await interaction.response.send_message("❌ There is no spam currently running.", ephemeral=True)


    # This was used for a Minecraft server hosted on my network
    # @commands.command(aliases=["IP", "ip"])
    # async def _get_IP(self, ctx):
    #     ip = get('https://api.ipify.org').text
    #     await ctx.send(f"The server IP is: {ip}")

    #TODO: Make a scale command to give a percentage of chance


async def setup(bot):
    await bot.add_cog(BasicCommands(bot))
