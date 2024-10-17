"""Miscs cog."""

import logging

from discord.ext import commands

logger = logging.getLogger(__name__)


class Misc(commands.Cog):
    """My first cog, for holding commands !"""

    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot

    @commands.hybrid_command()
    async def ping(self, ctx: commands.Context):
        """Ping the bot."""
        await ctx.send("Ping ! Pang ! Pong !")

    @commands.hybrid_command()
    @commands.has_any_role("modo", "Admin")
    async def sync(self, ctx: commands.Context):
        """Sync the / commands on discord."""
        await ctx.defer(ephemeral=False)
        await self.bot.tree.sync()
        await ctx.send("Sync OK")
        logger.info("Sync ok !")
        # cms = await self.bot.tree.fetch_commands()
        # print(cms)

    @commands.hybrid_command()
    @commands.has_any_role("modo", "Admin")
    async def sing(self, ctx: commands.Context):
        """Just sing."""
        await ctx.send("https://media.tenor.com/De6M1HsMZSEAAAAC/mariah-carey.gif")


async def setup(bot):
    await bot.add_cog(Misc(bot))
    logger.info("Misc cog added")
