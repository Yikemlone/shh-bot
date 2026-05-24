import asyncio
from discord import TextChannel, User
from discord.ext import commands
from datetime import datetime
from discord.ext import commands
from core.logger import logging, SHH_BOT

logger = logging.getLogger(SHH_BOT)

class TypingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.typing_users = {} 


    @commands.Cog.listener()
    async def on_typing(self, channel : TextChannel, user : User, when : datetime) -> None:
        """Listens for when a user starts typing."""
        self.typing_users[user.id] = when.now() 
        await asyncio.sleep(2) 
        if user.id in self.typing_users:
            start_time = self.typing_users[user.id]
            elapsed_time = (datetime.now() - start_time)
            if int(elapsed_time.seconds) >= 2:
                await self.send_typing_messages(channel, user)
        self.typing_users.pop(user.id, None)


    async def send_typing_messages(self, channel : TextChannel, user : User) -> None:
        """Sends the predefined messages after a typing delay."""
        messages = {
            "avatar": user.display_avatar.url,
            "message": "This you?",
            "GIF": "https://tenor.com/view/kermit-the-frog-drive-driving-gif-12873213"
        }

        for key, msg in messages.items():
            logger.info(f"Sending: {key}")
            await channel.typing()
            await asyncio.sleep(0.5)
            await channel.send(msg)


async def setup(bot):
    await bot.add_cog(TypingCog(bot))
