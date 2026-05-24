from discord import Interaction, HTTPException, DiscordException
from discord.app_commands import (AppCommandError, CommandInvokeError, TransformerError, 
                                  TranslationError, CheckFailure, NoPrivateMessage, 
                                  MissingRole, MissingAnyRole, MissingPermissions, 
                                  BotMissingPermissions, CommandOnCooldown, 
                                  CommandLimitReached, CommandAlreadyRegistered, 
                                  CommandSignatureMismatch, CommandNotFound, 
                                  MissingApplicationID, CommandSyncFailure)

from util.logger import logging, SHH_BOT 

logger = logging.getLogger(SHH_BOT)


async def on_command_errors(interaction: Interaction, error: AppCommandError):
    """Handles errors for application commands using a switch-like match-case."""
    logger.warning(f"Command '{interaction.command.name.upper()}' raised an error: {error}")

    message = {
        NoPrivateMessage: f"{interaction.user.mention} This command cannot be used in direct messages.",
        MissingRole: f"{interaction.user.mention} You are missing the required role to use this command.",
        MissingAnyRole: f"{interaction.user.mention} You need at least one of the required roles to use this command.",
        MissingPermissions: f"{interaction.user.mention} You lack the necessary permissions to use this command.",
        BotMissingPermissions: f"{interaction.user.mention} I lack the required permissions to execute this command.",
        CommandOnCooldown: f"{interaction.user.mention} This command is on cooldown. Try again in {getattr(error, 'retry_after', 0):.2f} seconds.",
        TransformerError: f"{interaction.user.mention} Invalid input provided. Please check your arguments.",
        TranslationError: f"{interaction.user.mention} There was an error translating the command.",
        CheckFailure: f"{interaction.user.mention} You do not meet the requirements to use this command.",
        CommandLimitReached: f"{interaction.user.mention} The command limit has been reached. Try again later.",
        CommandAlreadyRegistered: f"{interaction.user.mention} This command is already registered.",
        CommandSignatureMismatch: f"{interaction.user.mention} Incorrect command usage. Check the command's signature and try again.",
        CommandNotFound: f"{interaction.user.mention} That command does not exist.",
        MissingApplicationID: f"{interaction.user.mention} The bot's application ID is missing. Please contact an administrator.",
        CommandSyncFailure: f"{interaction.user.mention} Failed to sync commands. Please try again later.",
        CommandInvokeError: f"{interaction.user.mention} There was an internal error while processing your command.",
        HTTPException: f"{interaction.user.mention} An HTTP error occurred while processing your request.",
        AppCommandError: f"{interaction.user.mention} An application command error occurred.",
        DiscordException: f"{interaction.user.mention} An unexpected Discord error occurred."
    }.get(type(error), f"{interaction.user.mention} An unknown error occurred. Please try again later.")

    await interaction.response.send_message(message, ephemeral=True)