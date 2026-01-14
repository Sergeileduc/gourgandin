#!/usr/bin/python3
"""Miscs cog."""

import logging

import discord
from discord import app_commands, ui
from discord.ext import commands

logger = logging.getLogger(__name__)


class CodeModal(ui.Modal, title="My code modal"):
    answer = ui.TextInput(label="Entrez votre code", required=True, style=discord.TextStyle.long)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            content=f"# Code {self.lang} :\n```{self.lang}\n{self.answer}```"
        )


class Code(commands.Cog):
    """Mardown some code."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="code")
    @app_commands.choices(
        choices=[
            app_commands.Choice(name="Python", value="python"),
            app_commands.Choice(name="html", value="html"),
            app_commands.Choice(name="css", value="css"),
            app_commands.Choice(name="json", value="json"),
        ]
    )
    async def code(
        self,
        interaction: discord.Interaction,
        choices: app_commands.Choice[str],
    ):
        codemodal = CodeModal(title="Entrez votre code")
        codemodal.lang = choices.value
        await interaction.response.send_modal(codemodal)


async def setup(bot):
    await bot.add_cog(Code(bot))
    logger.info("Cog code added")
