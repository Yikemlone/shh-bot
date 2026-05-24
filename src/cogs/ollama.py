from discord import Interaction, app_commands
import ollama
import asyncio
from discord.ext import commands
from core.logger import logging, SHH_BOT

logger = logging.getLogger(SHH_BOT)

class Ollama(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.llm_model = "dolphin-mixtral:latest"


    @app_commands.command(name="llm", description="Talk to an LLM")
    @app_commands.describe(message="The message you want to send to the LLM")
    async def ask_llm(self, interaction: Interaction, message : str):
        await interaction.response.defer()
        response = await asyncio.to_thread(self.get_ollama_response, message)
        logger.debug(f"{response["response"]}")
        await self.send_long_message(interaction, response["response"])


    def get_ollama_response(self, message):
        """This function runs in a separate thread to avoid blocking the event loop"""
        return ollama.generate(model=self.llm_model, prompt=message)


    async def send_long_message(self, interaction : Interaction, message):
        """Send long messages by splitting them into multiple parts"""
        message_chunks = [message[i:i+2000] for i in range(0, len(message), 2000)]
        for chunk in message_chunks:
            await interaction.followup.send(chunk)


async def setup(bot):
    await bot.add_cog(Ollama(bot))