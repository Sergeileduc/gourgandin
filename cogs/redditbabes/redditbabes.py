#!/usr/bin/python3
"""Cog to get daily on bonjourmadame picture."""

# Instructions :
# put a file named redditbabes.txt in the directory
# each line will be a subreddit that you want to get hourly

import logging
import os
from pathlib import Path

import asyncpraw  # pip install asyncpraw
import discord
from discord import app_commands
from discord.ext import commands, tasks

from .reddit_client import get_reddit_client
from .reddit_poster import RedditPoster

logger = logging.getLogger(__name__)

MAX_TRY = 5
HISTORY_LIMIT = 500

########################


async def load_subreddits(filename: str = "redditbabes.txt") -> list[str]:
    """
    Charge la liste des subreddits à parcourir depuis un fichier local.

    Args:
        filename (str): Nom du fichier contenant les subreddits.

    Returns:
        list[str]: Une liste de noms de subreddits. Retourne une liste vide si le fichier est introuvable.
    """  # noqa: E501
    path = Path(__file__).parent / filename
    try:
        with path.open(mode="r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        logger.error("Fichier %s introuvable.", filename)
        return []


async def save_subreddits(subreddits: list[str], filename: str = "redditbabes.txt") -> None:
    """
    Sauvegarde la liste des subreddits dans un fichier local.

    Args:
        subreddits (list[str]): La liste des noms de subreddits à enregistrer.
        filename (str): Nom du fichier où écrire les subreddits.

    Returns:
        None
    """
    path = Path(__file__).parent / filename
    try:
        with path.open(mode="w", encoding="utf-8") as f:
            for sub in subreddits:
                f.write(f"{sub}\n")
        logger.info("Liste des subreddits sauvegardée dans %s.", filename)
    except Exception as e:
        logger.error("Erreur lors de la sauvegarde du fichier %s : %s", filename, e)


########################


class RedditGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="reddit", description="Gestion des subreddits")

    @app_commands.command(name="list", description="Lister les subreddits")
    async def list_subs(self, interaction: discord.Interaction) -> None:
        subs = await load_subreddits()
        if not subs:
            await interaction.response.send_message("📂 Aucun subreddit enregistré.")
        else:
            msg = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(subs))
            await interaction.response.send_message(f"📜 Liste des subreddits :\n{msg}")

    @app_commands.command(name="add", description="Ajouter un subreddit")
    async def add_sub(self, interaction: discord.Interaction, name: str) -> None:
        subs = await load_subreddits()
        if name in subs:
            await interaction.response.send_message(f"⚠️ {name} est déjà dans la liste.")
            return
        subs.append(name)
        await save_subreddits(subs)
        await interaction.response.send_message(f"✅ {name} ajouté.")

    @app_commands.command(name="remove", description="Supprimer un subreddit")
    async def remove_sub(self, interaction: discord.Interaction, name: str) -> None:
        subs = await load_subreddits()
        if name not in subs:
            await interaction.response.send_message(f"❌ {name} n’est pas dans la liste.")
            return
        subs = [s for s in subs if s != name]
        await save_subreddits(subs)
        await interaction.response.send_message(f"🗑️ {name} supprimé.")


########################


class RedditBabes(commands.Cog):
    """Cog to get hourly babes from reddit and post them."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.reddit = get_reddit_client()  # depuis reddit_client.py
        self.poster = RedditPoster(
            reddit=self.reddit,
            channel=self.bot.nsfw_channel,  # type: ignore[attr-defined]
            bot_user=self.bot.user,  # type: ignore[arg-type]
        )  # depuis reddit_poster.py
        self.babes.start()  # pylint: disable=no-member

        # 👉 Ajout du groupe slash commands au tree
        self.bot.tree.add_command(RedditGroup())

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        """Send reddit in another channel on reaction."""

        if payload.channel_id != self.bot.nsfw_channel.id:  # type: ignore[attr-defined]
            return

        # message: discord.Message = await self.bot.get_channel(payload.channel_id).fetch_message(
        #     payload.message_id
        # )  # noqa: E501
        channel = self.bot.get_partial_messageable(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)

        author = payload.member.display_name if payload.member else None
        # we fetch previous messages, to get the message just before the image
        messages = [mess async for mess in message.channel.history(limit=2, before=message)]
        # the previous message shoud be :
        desc_message: discord.Message = messages[0]
        # sending both messages
        await self.bot.nsfw_channel_manual.send(  # type: ignore[attr-defined]
            content=f"{author} vous a partagé ceci :", embed=desc_message.embeds[0]
        )
        await self.bot.nsfw_channel_manual.send(message.content)  # type: ignore[attr-defined]

    @tasks.loop(hours=1)  # checks the babes subreddit every hour
    async def babes(self) -> None:
        """
        Tâche périodique qui interroge les subreddits configurés et publie les nouveaux contenus dans le canal Discord.
        """  # noqa: E501
        logger.info("🕒 Entering hourly task.")
        subreddits = await load_subreddits()
        if not subreddits:
            logger.warning("Aucun subreddit à traiter.")
            return

        for sub in subreddits:
            try:
                await self.poster.process_subreddit(sub)
            except Exception as e:
                logger.error("Erreur lors du traitement du subreddit %s : %s", sub, e)

        logger.info("🕒 Exiting hourly task.")

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
    logger.info("⚙️ Cog RedditBabes og added")


# main is for debugging purpose
if __name__ == "__main__":  # python -m cogs.redditbabes.redditbabes from root folder
    import asyncio
    import json  # noqa: F401
    from collections.abc import AsyncIterable, AsyncIterator
    from typing import TypeVar

    from asyncpraw.models import Submission
    from dotenv import load_dotenv

    T = TypeVar("T")

    # Parse a .env file and then load all the variables found as environment variables.
    load_dotenv()

    REDDIT_ID = os.getenv("REDDIT_ID")
    REDDIT_SECRET = os.getenv("REDDIT_SECRET")
    REDDIT_AGENT = os.getenv("REDDIT_AGENT")

    # logger.setLevel(logging.DEBUG)
    # console_handler = logging.StreamHandler()
    # console_handler.setLevel(logging.DEBUG)
    # logger.addHandler(console_handler)
    logging.basicConfig(level=logging.INFO)

    logger.debug("ceci est un message de debug")

    async def aenumerate[T](
        aiter: AsyncIterable[T], start: int = 0
    ) -> AsyncIterator[tuple[int, T]]:
        index = start
        async for item in aiter:
            yield index, item
            index += 1

    async def askip(aiterable, n):
        it = aiterable.__aiter__()
        for _ in range(n):
            try:
                await it.__anext__()
            except StopAsyncIteration:
                return
        async for item in it:
            yield item

    async def extract_gallery_images(submission: Submission) -> list[str]:
        """
        Retourne toutes les URLs d'images d'une submission Reddit.
        Fonctionne même si l'API ne fournit pas media_metadata (cas NSFW).
        """

        images: list[str] = []

        # 1) Si l'API fournit media_metadata → utiliser ça en priorité
        if getattr(submission, "media_metadata", None):
            print("Méthode 1")
            images = []
            for item in submission.media_metadata.values():
                if "s" in item and "u" in item["s"]:
                    url = item["s"]["u"]
                    url = url.replace("&amp;", "&")
                    images.append(url)
            if images:
                return images

        # 2) Si c'est une image simple (pas galerie)
        if submission.url.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".webp")):
            return [submission.url]
        return []

    async def main():
        from .reddit_models import RedditSubmissionInfo
        from .reddit_tools import resolve_submission

        reddit = asyncpraw.Reddit(
            client_id=REDDIT_ID, client_secret=REDDIT_SECRET, user_agent=REDDIT_AGENT
        )
        logger.info("Reddit ok.")

        # # List of subreddits
        # subreddits = await load_subreddits("redditbabes_test.txt")
        subreddits = [
            "NSFWFashion",
        ]

        for sub in subreddits:
            subreddit = await reddit.subreddit(sub, fetch=True)
            logger.info("fetching %s", sub)
            # Iterate on each submission
            async for index, submission in aenumerate(askip(subreddit.new(limit=7), 6), start=1):
                if submission.stickied:
                    continue
                if submission.removed_by_category == "deleted":
                    logger.info("continue because deleted : %s", submission)
                    continue
                submission = await resolve_submission(submission)

                sub_object: RedditSubmissionInfo = RedditSubmissionInfo(submission=submission)
                print(f"{index}: {sub_object}")
                print(sub_object.title)
                print(sub_object.is_younger())
                print("---------------")
        await reddit.close()

        interesting = [  # noqa: F841
            "title",
            "is_gallery",
            "gallery_data",
            "is_meta",
            "is_self",
            "is_video",
            "media",
            "media_embed",
            "media_metadata",
            "media_only",
            "name",
            "over_18",
            "pinned",
            "url",
            "url_overridden_by_dest",
        ]

        # for attr in interesting:
        #     value = getattr(submission, attr, None)
        #     if attr == "media_metadata":
        #         print(json.dumps(submission.media_metadata, indent=2, ensure_ascii=False))
        #     else:
        #         print("media_metadata : ")
        #         print(f"{attr}: {value!r}")

        # # await submission.load()
        # # print(dir(submission))

    asyncio.run(main())
