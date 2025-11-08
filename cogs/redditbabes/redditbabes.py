#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""Cog to get daily on bonjourmadame picture."""

# Instructions :
# put a file named redditbabes.txt in the directory
# each line will be a subreddit that you want to get hourly

from typing import Optional
from dataclasses import dataclass, field
import os
import logging
from pathlib import Path

import asyncpraw  # pip install asyncpraw
from asyncpraw.models import Submission

import discord
from discord.ext import commands, tasks

from utils.tools import get_last_bot_messages

from .reddit_client import get_reddit_client
from .reddit_poster import RedditPoster


logger = logging.getLogger(__name__)

MAX_TRY = 5
HISTORY_LIMIT = 500

########################


async def load_subreddits() -> list[str]:
    """
    Charge la liste des subreddits à parcourir depuis le fichier local `redditbabes.txt`.

    Returns:
        list[str]: Une liste de noms de subreddits. Retourne une liste vide si le fichier est introuvable.
    """
    try:
        p = Path(__file__).parent / "redditbabes.txt"
        with open(p, mode='r', encoding='utf-8') as f:
            return f.read().splitlines()
    except FileNotFoundError:
        logger.error("Fichier redditbabes.txt introuvable.")
        return []


########################


class RedditBabes(commands.Cog):
    """Cog to get hourly babes from reddit and post them."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.reddit = get_reddit_client()  # depuis reddit_client.py
        self.poster = RedditPoster(reddit=self.reddit,
                                   channel=self.bot.nsfw_channel,
                                   bot_user=self.bot.user,
                                   )  # depuis reddit_poster.py
        self.babes.start()  # pylint: disable=no-member

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """Send reddit in another channel on reaction."""

        if payload.channel_id != self.bot.nsfw_channel.id:
            return

        message: discord.Message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
        author = payload.member.display_name
        # we fetch previous messages, to get the message just before the image
        messages = [mess async for mess in message.channel.history(limit=2, before=message)]
        # the previous message shoud be :
        desc_message: discord.Message = messages[0]
        # sending both messages
        await self.bot.nsfw_channel_manual.send(content=f"{author} vous a partagé ceci :",
                                                embed=desc_message.embeds[0])
        await self.bot.nsfw_channel_manual.send(message.content)

    @tasks.loop(hours=1)  # checks the babes subreddit every hour
    async def babes(self) -> None:
        """
        Tâche périodique qui interroge les subreddits configurés et publie les nouveaux contenus dans le canal Discord.
        """
        logger.info("Entering hourly task.")
        subreddits = await load_subreddits()
        if not subreddits:
            logger.warning("Aucun subreddit à traiter.")
            return

        for sub in subreddits:
            try:
                await self.poster.process_subreddit(sub)
            except Exception as e:
                logger.error("Erreur lors du traitement du subreddit %s : %s", sub, e)

        logger.info("Exiting hourly task.")

    @babes.before_loop
    async def before_babes(self):
        """Intiliaze babes loop."""
        await self.bot.wait_until_ready()


async def setup(bot):
    """
    Sets up the RedditBabes cog for the provided Discord bot instance.

    This asynchronous function adds the RedditBabes cog to the bot and logs a message
    indicating the successful addition of the cog.

    Args:
        bot: The Discord bot instance to which the cog will be added.

    Returns:
        None
    """
    await bot.add_cog(RedditBabes(bot))
    logger.info("RedditBabes cog added")


# main is for debugging purpose
if __name__ == "__main__":
    import asyncio
    from dotenv import load_dotenv
    from .reddit_models import RedditSubmissionInfo

    # Parse a .env file and then load all the variables found as environment variables.
    load_dotenv()

    REDDIT_ID = os.getenv("REDDIT_ID")
    REDDIT_SECRET = os.getenv("REDDIT_SECRET")
    REDDIT_AGENT = os.getenv("REDDIT_AGENT")

    logger.setLevel(logging.DEBUG)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    logger.addHandler(console_handler)

    async def main():
        reddit = asyncpraw.Reddit(client_id=REDDIT_ID,
                                  client_secret=REDDIT_SECRET,
                                  user_agent=REDDIT_AGENT)

        logger.info("Reddit ok.")

        # List of subreddits
        try:
            p = Path(__file__).parent / "redditbabes.txt"
            with open(p, mode='r', encoding='utf-8') as f:
                subreddits = f.read().splitlines()
        except FileNotFoundError:
            logger.error("cogs/redditbabes.txt is missing")
            subreddits = []

        for sub in subreddits:
            subreddit = await reddit.subreddit(sub, fetch=True)
            logger.info("fetching %s", sub)
            # Iterate on each submission
            async for submission in subreddit.new(limit=10):
                if submission.stickied:
                    continue
                if submission.removed_by_category == "deleted":
                    logger.info("continue because deleted : %s", submission)
                    continue
                sub_object: RedditSubmissionInfo = RedditSubmissionInfo(submission=submission)
                print(sub_object)
                print("---------------")
        await reddit.close()

    asyncio.run(main())
