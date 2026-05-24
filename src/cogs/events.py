from discord.ext import commands
from discord import Message, Interaction, Member, utils
from core.logger import logging, SHH_BOT

logger = logging.getLogger(SHH_BOT)

class Events(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.join_channel = "gamer"


    @commands.Cog.listener()
    async def on_message_edit(self, before : Message, after : Message):
        """This will send a message of the contents of the before and after of a message edit"""
        if before.author.bot or after.author.bot:
            return

        if before.content == after.content:
            return
    
        message_author = before.author.mention
        reply = (f"Look who's trying to hide something 😏\n\n"
                f"{message_author}'s message before edit: \"{before.content}\"\n\n"
                f"{message_author}'s message after edit: \"{after.content}\"")

        await after.channel.send(reply)


    @commands.Cog.listener()
    async def on_member_join(self, member : Member):
        """ When a new member joins, posts a message in chat"""
        try:
            logger.info(f"{member} has joined the server.")
            channel = utils.get(member.guild.text_channels, name=self.join_channel)
            await channel.send(f"{member.mention} has joined the server :).")
        except Exception as e:
            logger.error(e)


    @commands.Cog.listener()
    async def on_member_remove(self, member : Member):
        """ When a member leavs, posts a message in chat"""
        try:
            logger.info(f"{member} has left the server.")
            channel = utils.get(member.guild.text_channels, name=self.join_channel)
            await channel.send(f"{member.mention} has left the server :(.")
        except Exception as e:
            logger.error(e)

    # TODO: Add events for kick and ban for funny effect maybe

async def setup(bot):
    await bot.add_cog(Events(bot))