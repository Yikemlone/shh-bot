from typing import Callable
from discord import AudioSource, VoiceClient, Interaction, VoiceChannel
from discord.ext.voice_recv import VoiceRecvClient
from core.logger import logging, SHH_BOT

logger = logging.getLogger(SHH_BOT)

class VoiceClientManagerService():

    def __init__(self):
        self.channel : VoiceChannel = None
        self.voice_client : VoiceClient = None 

    def get_channel(self) -> VoiceChannel:
        """Returns the channel."""
        return self.channel

    def get_voice_client(self) -> VoiceClient:
        """Returns the voice client."""
        return self.voice_client
    
    async def move_to_channel(self, interaction: Interaction) -> None: 
        """Will leave current voice channel, to a new voice channel."""
        self.voice_client.stop()
        self.voice_client = await self.voice_client.disconnect() 
        self.channel = interaction.user.voice.channel
        self.voice_client = await self.channel.connect(cls=VoiceRecvClient)
        self.voice_client.set_davey(True)

    def stop(self) -> None:
        """Stops the voice client."""
        self.voice_client.stop()

    def resume(self) -> None:
        """Resumes the voice client."""
        self.voice_client.resume()

    async def disconnect(self) -> None:
        """Disconnects the voice client."""
        self.voice_client.stop()
        self.voice_client = await self.voice_client.disconnect()
        self.channel = None

    def pause(self) -> None:
        """Pauses the voice client."""
        self.voice_client.pause()

    def is_playing(self) -> bool:
        """Returns whether or not the voice client is playing."""
        return self.voice_client.is_playing()

    def is_paused(self) -> bool:
        """Returns whether or not the voice client is paused."""
        return self.voice_client.is_paused()

    def resume(self) -> None:
        """Resumes the voice client."""
        self.voice_client.resume()

    def start_recording(self, sink, *, after=None) -> None:
        """Starts recording audio from the voice channel."""
        self.voice_client.listen(sink, after=after)

    def stop_recording(self) -> None:
        """Stops recording and triggers the callback."""
        self.voice_client.stop_listening()

    def is_recording(self) -> bool:
        """Returns whether the voice client is recording."""
        return self.voice_client.is_listening()

    def play(self, song : AudioSource, after : Callable[[], None] = None) -> None:
        """Plays the song in the voice client."""
        self.voice_client.play(song, after=after)

    async def join_voice_channel(self, interaction : Interaction) -> bool:
        """The bot will try to connect to the VC the user is in."""
        if interaction.user.voice is None:
            return False
        
        user_channel_name = interaction.user.voice.channel.name

        try:
            if self.channel is None:
                logger.info(f"Joining VC: {user_channel_name}")
                self.channel = interaction.user.voice.channel
                self.voice_client = await self.channel.connect(cls=VoiceRecvClient)
                self.voice_client.set_davey(True)
            elif user_channel_name != str(self.channel):
                logger.info(f"Moving to join VC: {user_channel_name}")
                await self.move_to_channel(interaction)

            return True
        
        except Exception as ex:
            logger.error(f"Error joining the {user_channel_name} VC: {ex}")
