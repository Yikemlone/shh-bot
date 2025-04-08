import discord
import os
import asyncio
import discord.ext
import discord.ext.commands
from util.logger import logging, SHH_BOT
from util.util import is_guild_owner
from util.exceptionhandler import on_command_errors
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()   

logger = logging.getLogger(SHH_BOT)

# Define the intents, this is required for the bot to work
intents = discord.Intents.all()
intents.message_content = True

# Define the bot
bot = commands.Bot(command_prefix="!", intents=intents, voice_client=discord.VoiceClient)


async def load_extensions():
    """Loads all the cogs in the cogs folder."""
    for filename in os.listdir("cogs"):
        if filename.endswith(".py") and filename != "__init__.py":
           await bot.load_extension(f"cogs.{filename[:-3]}")

@bot.event
async def on_message(message):
    """ This function will be called whenever a message is sent in the server."""
    if message.author.bot: return
    await bot.process_commands(message)


@bot.event
async def on_ready():
    logger.info(f"Bot is ready. Logged in as {bot.user}")
    await bot.change_presence(activity=discord.Game("fiddles"), status=discord.Status.do_not_disturb)
    # bot.tree.on_error = on_command_errors

    try:
        synced = await bot.tree.sync()  # Syncs slash commands globally
        logger.info(f"Synced {len(synced)} commands.")

    except Exception as e:
        logger.error(f"Error syncing commands: {e}")


async def main():
    await load_extensions()
    await bot.start(os.getenv('BOT_TOKEN'))


if __name__ == "__main__":
    asyncio.run(main())
