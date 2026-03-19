"""Miscs cog."""

import logging

from discord.ext import commands

from utils.tools import get_ram_usage_mb

logger = logging.getLogger(__name__)


class Misc(commands.Cog):
    """My first cog, for holding commands !"""

    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot

    @commands.hybrid_command()
    async def ping(self, ctx: commands.Context) -> None:
        """Ping the bot."""
        await ctx.send("Ping ! Pang ! Pong !")
        logger.info("command !/ping was called")

    @commands.hybrid_command()
    @commands.has_any_role("modo", "Admin")
    async def sync(self, ctx: commands.Context) -> None:
        """Sync the / commands on discord."""
        await ctx.defer(ephemeral=False)
        await self.bot.tree.sync()
        await ctx.send("Sync OK")
        logger.info("Sync ok !")
        # cms = await self.bot.tree.fetch_commands()
        # print(cms)

    @commands.hybrid_command()
    @commands.has_any_role("modo", "Admin")
    async def sing(self, ctx: commands.Context) -> None:
        """Just sing."""
        await ctx.send("https://media.tenor.com/De6M1HsMZSEAAAAC/mariah-carey.gif")
        logger.info("command !/sing was called.")

    @commands.hybrid_command()
    @commands.has_any_role("modo", "Admin")
    async def ram(self, ctx: commands.Context) -> None:
        """Get ram usage."""
        ram = get_ram_usage_mb()
        logger.info("RAM used: %.2f MB", ram)
        await ctx.send(f"RAM actuelle : {ram:.1f} MB")


async def setup(bot):
    await bot.add_cog(Misc(bot))
    logger.info("⚙️ Misc cog added")
