#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""Cog to get daily on bonjourmadame picture."""

# Instructions :
# put a file named redditbabes.txt in the directory
# each line will be a subreddit that you want to get hourly

import os
import logging
from pathlib import Path

import asyncpraw  # pip install asyncpraw
import discord
from discord.ext import commands, tasks

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Parse a .env file and then load all the variables found as environment variables.
load_dotenv()

REDDIT_ID = os.getenv("REDDIT_ID")
REDDIT_SECRET = os.getenv("REDDIT_SECRET")
REDDIT_AGENT = os.getenv("REDDIT_AGENT")


class RedditBabes(commands.Cog):
    """Cog to get hourly babes from reddit and post them."""

    def __init__(self, bot):
        self.bot = bot
        self.babes.start()  # pylint: disable=no-member

    @tasks.loop(hours=1)  # checks the babes subreddit every hour
    async def babes(self):
        """Send babes from reddit."""
        # allready posted babes list
        logger.info("Entering hourly task.")
        nsfw_channel_history = [mess async for mess in self.bot.nsfw_channel.history(limit=500)]  # noqa: E501
        print(f"{nsfw_channel_history=}")
        last_bot_messages = [message.content
                             for message in nsfw_channel_history
                             if message.author == self.bot.user]
        print("----------------------------------------------------------------")
        print(len(last_bot_messages))
        print(last_bot_messages)
        print("----------------------------------------------------------------")
        logger.info("Messages fetched.")
        # Reddit client
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

        # Iterate on our subreddits
        for sub in subreddits:
            subreddit = await reddit.subreddit(sub, fetch=True)
            logger.info("fetching %s", sub)
            # Iterate on each submission
            async for submission in subreddit.new(limit=10):
                if submission.stickied:
                    continue
                url = submission.url
                print(url)
                if url not in last_bot_messages:
                    print("Not in last_bot_messages, sending")
                    # TODO: I let some codes, if we want to change, with only sends
                    # or with a full embed (with the set_image thing)
                    # we can decide later.
                    # await self.bot.nsfw_channel.send(submission.title)
                    # await self.bot.nsfw_channel.send(url)
                    embed = discord.Embed(title=submission.title,
                                          url=f"https://www.reddit.com{submission.permalink}",
                                          description=sub
                                          )
                    # embed.set_image(url=url)
                    await self.bot.nsfw_channel.send(embed=embed)
                    await self.bot.nsfw_channel.send(url)
                else:
                    logger.info("Already in last_bot_messages, skipping")
        await reddit.close()
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
