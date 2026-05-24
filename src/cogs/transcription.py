import asyncio
import discord
from discord import app_commands, Interaction
from discord.ext import commands
from discord.ext.voice_recv import VoiceRecvClient
from services.voice.recorder import TranscriptionService
from core.logger import logging, SHH_BOT

logger = logging.getLogger(SHH_BOT)


class Transcription(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.transcription_service = TranscriptionService()

    @app_commands.command(name="record", description="Start recording voice in the current VC.")
    @app_commands.guild_only()
    async def record(self, interaction: Interaction):
        if interaction.user.voice is None:
            await interaction.response.send_message("You must be in a voice channel.", ephemeral=True)
            return

        vc = interaction.guild.voice_client
        if vc is None:
            vc = await interaction.user.voice.channel.connect(cls=VoiceRecvClient)
            vc.set_davey(True)
        elif interaction.user.voice.channel != vc.channel:
            await interaction.response.send_message("You must be in the same VC as the bot.", ephemeral=True)
            return

        if self.transcription_service.is_recording:
            await interaction.response.send_message("Already recording.", ephemeral=True)
            return

        self.transcription_service.start(vc, interaction.channel, self.bot.loop)
        await interaction.response.send_message("Recording started. Use `/stop` to end and transcribe.")

    @app_commands.command(name="stop", description="Stop recording and transcribe.")
    @app_commands.guild_only()
    async def stop(self, interaction: Interaction):
        vc = interaction.guild.voice_client
        if vc is None:
            await interaction.response.send_message("Bot is not in a voice channel.", ephemeral=True)
            return

        if not self.transcription_service.is_recording:
            await interaction.response.send_message("Not currently recording.", ephemeral=True)
            return

        self.transcription_service.stop(vc)
        await interaction.response.send_message("Recording stopped. Processing transcription...")


async def setup(bot):
    await bot.add_cog(Transcription(bot))
