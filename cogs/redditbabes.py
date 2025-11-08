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

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Parse a .env file and then load all the variables found as environment variables.
load_dotenv()

REDDIT_ID = os.getenv("REDDIT_ID")
REDDIT_SECRET = os.getenv("REDDIT_SECRET")
REDDIT_AGENT = os.getenv("REDDIT_AGENT")

########################


@dataclass
class RedditSubmissionInfo:
    submission: Submission
    post_url: str = field(init=False)
    subreddit: str = field(init=False)
    title: str = field(init=False)
    author: str = field(init=False)
    is_album: bool = field(init=False)
    image_count: int = field(init=False)
    image_url: Optional[str] = field(init=False)

    def __post_init__(self):
        self.post_url = self.submission.url
        self.subreddit_name = self.submission.subreddit.display_name
        self.title = self.submission.title
        self.author = str(self.submission.author)
        self.subreddit_name = self.submission.subreddit.display_name
        self.is_album = hasattr(self.submission, "media_metadata") and bool(self.submission.media_metadata)
        self.image_url = None
        self.image_count = 0
        logger.debug(self.post_url)

        if self.is_album:
            logger.info("that's an album %s", self.post_url)
            logger.info("getting the first image for %s", self.submission)
            self._extract_album_info()
        elif (self.submission.url.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp"))
              or "redgifs" in self.submission.url):
            self.image_url = self.submission.url
            self.image_count = 1
            logger.info("standard submission with one pic : %s", self.submission)
        else:
            logger.error("something bad happened with picture for submission %s, we got this url %s", self.post_url, self.image_url)
            raise RedditException("Impossible de trouver du contenu", self.submission.id)
        logger.debug("image url : %s", self.image_url)

    def _extract_album_info(self):
        try:
            items = self.submission.gallery_data.get("items", [])
            if not isinstance(items, list) or not items:
                raise RedditException("Aucune image trouvée dans l'album", self.submission.id)

            first_media_id = items[0].get("media_id")
            if not first_media_id:
                raise RedditException("media_id manquant dans le premier item", self.submission.id)

            image_info = self.submission.media_metadata.get(first_media_id, {})
            self.image_url = image_info.get("s", {}).get("u")
            if not self.image_url:
                raise RedditException("URL de l'image introuvable dans les métadonnées", self.submission.id)

            self.image_count = len(items)
        except (AttributeError, TypeError, KeyError) as e:
            raise RedditException(f"Erreur lors de l'extraction des images : {e}", self.submission.id)

    def to_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=self.title[:256],
            description=self.subreddit_name,
            url=f"https://www.reddit.com{self.submission.permalink}"
        )
        if self.is_album:
            embed.set_footer(text=f"Album de {self.image_count} images",
                             icon_url="https://images.emojiterra.com/twitter/v13.1/512px/1f4d6.png")
        # if self.image_url:
        #     embed.set_image(url=self.image_url)
        # embed.set_footer(text=f"Posté par u/{self.author}")
        return embed


class RedditException(Exception):
    def __init__(self, message: str, submission_id: str = None):
        self.submission_id = submission_id
        super().__init__(f"[RedditException] {message} (ID: {submission_id})" if submission_id else message)


class RedditBabes(commands.Cog):
    """Cog to get hourly babes from reddit and post them."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
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
    async def babes(self):
        """Send babes from reddit."""
        # allready posted babes list
        logger.info("Entering hourly task.")

        # we try to ask discord for history, but it can fail. return if
        try:
            nsfw_channel_history = [mess async for mess in self.bot.nsfw_channel.history(limit=500)]  # noqa: E501
        except discord.DiscordServerError as e:
            logger.warning(f"Erreur Discord 503 lors de la récupération de l'historique : {e}")
            return  # Quitte proprement, la tâche se relancera à la prochaine heure

        # print(f"{nsfw_channel_history=}")
        last_bot_messages = [message.content
                             for message in nsfw_channel_history
                             if message.author == self.bot.user]

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
                if submission.removed_by_category == "deleted":
                    logger.info("continue because deleted : %s", submission)
                    continue
                try:
                    sub_object: RedditSubmissionInfo = RedditSubmissionInfo(submission=submission)
                    if sub_object.image_url not in last_bot_messages:
                        # print("Not in last_bot_messages, sending")
                        # TODO: I let some codes, if we want to change, with only sends
                        # or with a full embed (with the set_image thing)
                        # we can decide later.
                        # await self.bot.nsfw_channel.send(submission.title)
                        # await self.bot.nsfw_channel.send(url)
                        embed = sub_object.to_embed()
                        # embed.set_image(url=url)  # this of send(url) line
                        await self.bot.nsfw_channel.send(embed=embed)
                        await self.bot.nsfw_channel.send(sub_object.image_url)
                    else:
                        logger.info("Already in last_bot_messages, skipping")
                except RedditException:
                    pass
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


# main is for debugging purpose
if __name__ == "__main__":
    import asyncio

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
                # print(sub_object)
                # print("---------------")
        await reddit.close()

    asyncio.run(main())
