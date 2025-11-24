"""Miscs cog."""

import io
import logging
import os

import aiohttp
import discord
from discord.ext import commands
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()

API_KEY = os.environ["API_ADULTDATA"]

ADULT_URL = "https://api.adultdatalink.com/pornpics/tag-image-links"


headers = {
    "accept": "application/json",
    "X-API-Key": API_KEY
}


class PronPics(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot

    @commands.hybrid_command()
    async def pornpics(self, ctx: commands.Context, tag: str):
        """Send images of a tag."""

        await ctx.defer(ephemeral=False)

        params = {"tag": tag}

        async with aiohttp.ClientSession() as session:
            async with session.get(ADULT_URL, params=params, headers=headers) as response:
                # print("Status:", response.status)
                if response.status == 200:
                    data = await response.json()
                    pics = data.get("urls", [])
                    for url in pics:
                        # print("Téléchargement:", url)
                        async with session.get(url) as img_resp:
                            if img_resp.status == 200:
                                img_data = await img_resp.read()
                                file = discord.File(io.BytesIO(img_data), filename=url.split("/")[-1])
                                await ctx.send(file=file)
                            else:
                                await ctx.send(f"Impossible de télécharger {url} (status {img_resp.status})")
                else:
                    text = await response.text()
                    print("Erreur:", response.status, text)

        await ctx.send(f"le tag était : {tag}")


async def setup(bot):
    await bot.add_cog(PronPics(bot))
    logger.info("PronPics cog added")
