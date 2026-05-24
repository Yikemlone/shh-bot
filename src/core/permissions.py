from discord import Interaction, Member
from util.logger import logging, SHH_BOT

logger = logging.getLogger(SHH_BOT)


def is_guild_owner(interaction: Interaction) -> bool:
    """Checks if the command user is the server owner."""
    return interaction.user.id == interaction.guild.owner_id

def user_has_role(interaction: Interaction, role_name: str) -> bool:
    """Checks if the user has the role."""
    return any(role.name.lower() == role_name.lower() for role in interaction.user.roles)

def is_moderator(user: Member) -> bool:
    """Checks if the user has moderation permissions."""
    mod_perms = ["manage_messages", "kick_members", "ban_members", "administrator"]
    return any(getattr(user.guild_permissions, perm, False) for perm in mod_perms)