import os
import asyncio
import yt_dlp as youtube_dl	
from discord import app_commands, Interaction, VoiceClient, Embed, Color, File, FFmpegPCMAudio
from discord import ClientException
from discord.ext import commands
from services.api.youtube import YouTubeConnection
from services.api.spotify import SpotifyConnection 
from core.logger import logging, SHH_BOT
from services.music.queue import QueueManagerService
from services.voice.clientmanager import VoiceClientManagerService
from services.music.song import SongService

logger = logging.getLogger(SHH_BOT)


class Music(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.queue_manager = QueueManagerService()
        self.voice_manager = VoiceClientManagerService()
        self.song_service = SongService()


    @app_commands.command(name="leave", description="This will make the bot leave the VC.")
    @app_commands.guild_only()
    async def leave(self, interaction : Interaction):
        """The bot will leave the VC it is currently in."""
        channel = self.voice_manager.get_channel()
        await self.voice_manager.disconnect()
        self.queue_manager.reset_queue()
        await interaction.response.send_message(f"{interaction.user.mention} has left the {channel} VC.")
        logger.info(f"Bot has left the {channel} VC.")


    @app_commands.command(name="play", description="This will play the song that is passed in.")
    @app_commands.describe(song_name="The name of the song you want to play. This can be a URL.")
    @app_commands.describe(artist="The name of the artist for the song.")
    @app_commands.guild_only()
    # TODO: Add a artist optional argument.
    async def play(self, interaction : Interaction, song_name : str, artist : str = None):
        """Adds the song to a queue list, joins the VC the user is in and then it will try to play the songs in the queue."""
        try:
            await interaction.response.defer()
            joined_voice_channel = await self.voice_manager.join_voice_channel(interaction)
            
            if joined_voice_channel:
                message = await self.try_to_play_song(interaction, song_name)
                await interaction.followup.send(message)
            else:
                await interaction.followup.send(f"{interaction.user.mention} you must be in a VC to play music.")

        except Exception as ex:
            logger.error(ex)


    @app_commands.command(name="skip", description="This will skip the current song and play the next song in the queue.")
    @app_commands.guild_only()
    async def skip(self, interaction: Interaction):
        """Updates the queue and plays the next song."""  
        skipped_current_song = self.queue_manager.get_current_song()
        song_queue = self.queue_manager.get_song_queue()

        if len(song_queue) == 0:
            logger.warning("No more songs in the queue from the skip method")
            await interaction.response.send_message(f"{interaction.user.mention} no more songs in queue. Queue some with the /queue command and a *song name*.")
            return

        self.voice_manager.stop() # Becasue of the callback function, stopping the current song will update queue and play the next song
        await interaction.response.send_message(f"{interaction.user.mention} skipping **{skipped_current_song["song"]}** by **{skipped_current_song["name"]}**. Now playing **{song_queue[0]["song"]}** by **{song_queue[0]["name"]}**.")


    @app_commands.command(name="pause", description="This will pause the song that is currently playing.")
    @app_commands.guild_only()
    async def pause(self, interaction: Interaction):
        """Pauses the song that is currently playing."""
        current_song = self.queue_manager.get_current_song()
        self.voice_manager.pause()
        await interaction.response.send_message(f"{interaction.user.mention} pausing **{current_song["song"]}** by **{current_song["name"]}**.")


    @app_commands.command(name="resume", description="This will resume a song that was playing.")
    @app_commands.guild_only()
    async def resume(self, interaction: Interaction):
        """Resumes a song that was playing."""
        current_song = self.queue_manager.get_current_song()        
        self.voice_manager.play(self.song_service.get_song_source())
        await interaction.response.send_message(f"{interaction.user.mention} resuming **{current_song["song"]}** by **{current_song["name"]}**.")


    @app_commands.command(name="loop", description="This will loop the current songs in the queue.")
    @app_commands.guild_only()    
    async def loop(self, interaction: Interaction):
        """Will set the bot to loop the songs in the queue and reset queue when no longer looping."""
        if self.queue_manager.isLooping():
            self.queue_manager.reset_queue()
            await interaction.response.send_message(f"{interaction.user.mention} no longer looping songs :x:")
        else:
            await interaction.response.send_message(f"{interaction.user.mention} now looping songs :repeat:")
        self.queue_manager.toggleLooping()
        logger.info(f"Song queue looping: {self.queue_manager.isLooping()}")


    @app_commands.command(name="queue", description="Displays a list of current songs in the queue.")
    @app_commands.guild_only()   
    async def queue(self, interaction: Interaction):
        """Will send the queue as a discord embed with an image."""
        await interaction.response.defer()

        if not self.queue_manager.isTherePlayableSongs():
            logger.debug(f"No songs in queue.")
            await interaction.followup.send(f"{interaction.user.mention} no more songs in queue. Queue some with the /queue command and a *song name*.")
            return
        
        current_song = self.queue_manager.get_current_song()
        song_queue = self.queue_manager.get_song_queue()
        image_path = os.path.join("src", "resources", "images", "Skelly-thumbs-up.gif")
        embed = Embed(title="Song Queue",color=Color.red())

        embed.add_field(name=":musical_note: Now Playing", value=f"**{current_song['song']}** by **{current_song['name']}**", inline=False)
    
        for index, song in enumerate(song_queue):
            if song is not None:
                artist_name = song["name"]
                song_name = song["song"]
                embed.add_field(name=f"#{index + 1}", value=f"**{song_name}** by **{artist_name}**", inline=True)

        if os.path.exists(image_path): 
            image_file = File(image_path, filename="Skelly-thumbs-up.gif")
            embed.set_image(url="attachment://Skelly-thumbs-up.gif")
            await interaction.followup.send(embed=embed, file=image_file) 
        else:
            await interaction.followup.send(embed=embed)  

    ## TODO ADD A COMMAND TO REMOVE SONG FROM QUEUE OR LAST SONG

    async def try_to_play_song(self, interaction : Interaction, song_name : str) -> str:
        """Will try to play the song that was passed in. If the bot is already playing a song, it will add the song to the queue."""
        try:
            current_song = self.queue_manager.get_current_song()
            song_queue = self.queue_manager.get_song_queue()
            song_details = await self.song_service.get_song_details(song_name)

            if song_details is None:
                return f"{interaction.user.mention} couldn't find song details for that query."

            if self.voice_manager.is_playing():
                self.queue_manager.add_to_queue(song_details)
                return f"{interaction.user.mention} the bot is already playing a song. Added {song_queue[-1]["URL"]} to queue."
            elif self.voice_manager.is_paused():
                self.queue_manager.add_to_queue(song_details)
                self.voice_manager.resume()
                return f"{interaction.user.mention} resuming {current_song["song"]} by {current_song["name"]}. Added {song_queue[-1]["URL"]} to queue."
            else:
                self.queue_manager.set_current_song(song_details)

            self.play_current_song(song_details["URL"]) 
            
            return f"{interaction.user.mention} now playing **{song_details['song']}** by **{song_details['name']}**. {song_details["URL"]}"
        
        except Exception as ex:
            logger.error(f"An unknown exception occurred: {ex}")
            return f"{interaction.user.mention} unknown error with playing a song."
    

    def play_current_song(self, song_url : str) -> None:
        """Will play the song that was passed in."""
        self.song_service.prep_soung_source(song_url)
        self.voice_manager.play(self.song_service.get_song_source(), after=self.after_playback)


    def after_playback(self, error):
        """Will be called after the current song has finished playing."""
        if error:
            logger.error(f"Playback error: {error}")
        
        self.queue_manager.update_queue()
        current_song = self.queue_manager.get_current_song()

        if not current_song:
            logger.warning("No more songs in the queue.")
            return 
        
        if self.voice_manager.is_playing(): 
            logger.warning("Tried to play a song while another is already playing.")
            return

        if not self.voice_manager.get_channel():
            logger.warning("Tried to play next song when not in a voice channel.")
            return

        if not self.voice_manager.get_voice_client():
            logger.warning("Tried to play music without a voice client.")
            return

        logger.info(f"Playing next song: {current_song['song']} by {current_song['name']}.")
        self.play_current_song(current_song["URL"])


async def setup(bot):
    await bot.add_cog(Music(bot))
