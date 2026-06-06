import os
import discord
from discord import app_commands, Interaction
from discord.ext import commands
from services.taskstore import TaskStore
from core.logger import logging, SHH_BOT

logger = logging.getLogger(SHH_BOT)


class Tasks(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self._store = TaskStore()

    @app_commands.command(name="board", description="Get the Kanban board link")
    @app_commands.guild_only()
    async def board(self, interaction: Interaction):
        board_url = os.getenv("BOARD_URL", "http://localhost:8080")
        embed = discord.Embed(
            title="Kanban Board",
            description=f"View your task board here:\n{board_url}",
            color=discord.Color.blurple(),
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="tasks", description="List all tasks")
    @app_commands.guild_only()
    async def tasks(self, interaction: Interaction):
        all_tasks = await self._store.list_all()
        if not all_tasks:
            await interaction.response.send_message("No tasks yet.")
            return

        lines = []
        for t in all_tasks:
            status_emoji = {"todo": "\u26aa", "in_progress": "\U0001f7e1", "done": "\U0001f7e2"}
            emoji = status_emoji.get(t.status, "\u26aa")
            lines.append(f"{emoji} **{t.title}** (`{t.id}`) — {t.priority}")

        chunks = [lines[i:i+20] for i in range(0, len(lines), 20)]
        await interaction.response.send_message(
            f"**{len(all_tasks)} tasks**\n" + "\n".join(chunks[0])
        )
        for chunk in chunks[1:]:
            await interaction.followup.send("\n".join(chunk))

    @app_commands.command(name="task-add", description="Manually add a task")
    @app_commands.describe(
        title="Task title",
        description="Task description",
        priority="Priority level",
    )
    @app_commands.guild_only()
    async def task_add(
        self,
        interaction: Interaction,
        title: str,
        description: str = "",
        priority: str = "medium",
    ):
        if priority not in ("low", "medium", "high", "critical"):
            await interaction.response.send_message(
                "Priority must be: low, medium, high, or critical.", ephemeral=True
            )
            return

        task = await self._store.create(
            title=title,
            description=description,
            priority=priority,
            
            created_by=str(interaction.user.id),
        )
        await interaction.response.send_message(
            f"Task created: **{task.title}** (`{task.id}`)"
        )


async def setup(bot):
    await bot.add_cog(Tasks(bot))
