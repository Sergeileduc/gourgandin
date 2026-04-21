#!/usr/bin/python3
"""Cog to get daily on bonjourmadame picture."""

import datetime

# from pytz import timezone
import logging
import os
from pathlib import Path

import discord
from discord.ext import commands, tasks
from httpx import AsyncClient
from selectolax.parser import HTMLParser

from gourgandin import NSFW_BOT_CHANNEL

logger = logging.getLogger(__name__)

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    )
}


async def latest_madame():
    """Fetch latest bonjourmadame img

    Returns:
        str: image url
        str: image description
        str: book if exist, or None
    """
    url = "https://www.bonjourmadame.fr/"

    async with AsyncClient(
        headers=headers,
        follow_redirects=True,
        timeout=10.0,
    ) as client:
        resp = await client.get(url)
        resp.raise_for_status()

    # print(resp.text)

    tree = HTMLParser(resp.text)

    # Selectolax: CSS selectors identiques à BS4
    content = tree.css_first("div.post-content > p")
    title_node = tree.css_first("header.post-header > h1 > a")

    title_txt = title_node.text(strip=True) if title_node else None

    # Book link
    book = None
    if content:
        a = content.css_first("a[href]")
        if a:
            book = a.attributes.get("href")

    # Image URL
    image_url = None
    if content:
        img = content.css_first("img[src]")
        if img:
            image_url = img.attributes.get("src", "").split("?")[0]

    return image_url, title_txt, book


class BonjourMadame(commands.Cog):
    """Cog for the loop fetching BonjourMadame"""

    def __init__(self, bot, guild_id, nsfw_channel_name):
        self.bot = bot
        self.guild_id = guild_id
        self.nsfw_channel_name = nsfw_channel_name

    @commands.Cog.listener()
    async def on_ready(self):
        guild = self.bot.get_guild(self.guild_id)
        self.nsfw_channel = discord.utils.get(guild.text_channels, name=self.nsfw_channel_name)

        if not self.bonjour_madame.is_running():
            self.bonjour_madame.start()
            logger.info("on_ready finished.")

    # @tasks.loop(hours=24)
    @tasks.loop(
        time=datetime.time(hour=9, minute=30)
    )  # THIS WORKS, but with an offset (9h30 actually triggers at 10h30 in winter)  # noqa: E501
    async def bonjour_madame(self):
        """Send daily bonjourmadame."""
        if not 0 <= datetime.date.today().weekday() <= 4:
            return
        url, title, book = await latest_madame()
        logger.info("try to post madame with %s / %s / %s", url, title, book)
        if url:
            await self.nsfw_channel.send(title)
            await self.nsfw_channel.send(url)
            logger.info("madame sent")
        if book:
            try:
                p = Path(__file__).parent / "bonjour_exclude.txt"
                with open(p, encoding="utf-8") as f:
                    excludes = f.read().splitlines()
            except FileNotFoundError:
                logger.error("cogs/bonjour_excludes.txt is missing")
                excludes = []
            if any(excl in book for excl in excludes):
                logger.info("bonjourmadame book was found, but excluded")
            else:
                await self.bot.nsfw_channel.send(book)
                logger.info("madame had a book, sent.")

    @bonjour_madame.before_loop
    async def before_bonjour_madame(self):
        """Intiliaze bonjour_madame loop."""
        # await self.bot.wait_until_ready()
        logger.info("Bonjour loop OK")
        # await asyncio.sleep(41400)  # Wait 10hours 30min, to lauch at 10:30AM


async def setup(bot):
    """
    Sets up the LeMonde cog for the provided Discord bot instance.

    This asynchronous function adds the BonjourMadame cog to the bot and logs a message
    indicating the successful addition of the cog.

    Args:
        bot: The Discord bot instance to which the cog will be added.
        guild_id (int): main guild id
        nsfw_channel_name (str): name to search for the nsfw channel used by bot
    Returns:
        None
    """
    guild_id = int(os.getenv("GUILD_ID"))
    # nsfw_channel = os.getenv("NSFW_CHANNEL")
    # nsfw_manual = os.getenv("NSFW_MANUAL_CHANNEL")
    await bot.add_cog(
        BonjourMadame(
            bot,
            guild_id=guild_id,
            nsfw_channel_name=NSFW_BOT_CHANNEL,
        )
    )
    logger.info("BonjourMadame cog added")


# main is for debugging purpose
if __name__ == "__main__":
    import asyncio

    logger.setLevel(logging.DEBUG)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    logger.addHandler(console_handler)

    async def main():
        url, title, book = await latest_madame()
        print(url)
        print(title)

    asyncio.run(main())
