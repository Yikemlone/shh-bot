import asyncio
import discord
from discord import app_commands, Interaction
from discord.ext import commands
from discord.ext.voice_recv import VoiceRecvClient
from services.voice.recorder import TranscriptionService
from core.logger import logging, SHH_BOT

logger = logging.getLogger(SHH_BOT)

VOICE_CONNECT_RETRIES = 2
VOICE_CONNECT_TIMEOUT = 45.0


class Transcription(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.transcription_service = TranscriptionService()

    async def _connect_voice(self, channel) -> VoiceRecvClient:
        last_error = None
        for attempt in range(VOICE_CONNECT_RETRIES + 1):
            try:
                vc = await channel.connect(
                    cls=VoiceRecvClient,
                    timeout=VOICE_CONNECT_TIMEOUT,
                )
                vc.set_davey(True)
                return vc
            except (asyncio.TimeoutError, asyncio.CancelledError) as e:
                last_error = e
                logger.warning(f"Voice connect attempt {attempt + 1}/{VOICE_CONNECT_RETRIES + 1} failed: {e}")
                if attempt < VOICE_CONNECT_RETRIES:
                    await asyncio.sleep(2.0)
        raise last_error  # type: ignore[misc]

    @app_commands.command(name="record", description="Start recording voice in the current VC.")
    @app_commands.describe(keep_wav="Keep the lossless WAV file locally for podcast use (may use disk space)")
    @app_commands.guild_only()
    async def record(self, interaction: Interaction, keep_wav: bool = False):
        if interaction.user.voice is None:
            await interaction.response.send_message("You must be in a voice channel.", ephemeral=True)
            return

        vc = interaction.guild.voice_client
        if vc is None:
            try:
                vc = await self._connect_voice(interaction.user.voice.channel)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                await interaction.response.send_message(
                    "Could not connect to the voice channel (timed out). "
                    "This is usually a network/firewall issue — ensure UDP ports 50000-65535 are open.",
                    ephemeral=True,
                )
                return
        elif interaction.user.voice.channel != vc.channel:
            await interaction.response.send_message("You must be in the same VC as the bot.", ephemeral=True)
            return

        if self.transcription_service.is_recording:
            await interaction.response.send_message("Already recording.", ephemeral=True)
            return

        self.transcription_service.start(vc, interaction.channel, self.bot.loop, keep_wav=keep_wav)
        await interaction.response.send_message("Recording started. Use `/stop` to end and transcribe." + (" WAV will be kept." if keep_wav else ""))

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
