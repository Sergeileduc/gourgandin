import logging

import asyncpraw  # pip install asyncpraw
import discord

from utils.tools import fetch_history

from .reddit_client import fetch_new_submissions
from .reddit_models import RedditException

logger = logging.getLogger(__name__)


class RedditPoster:
    """
        Gère la récupération et la publication de contenus Reddit dans un canal Discord.

        Cette classe encapsule les dépendances nécessaires pour publier des images issues de Reddit
        dans un canal Discord. Elle permet de traiter plusieurs subreddits tout en évitant les doublons
    grâce à une mémoire des derniers messages envoyés par le bot.

        Args:
            reddit (asyncpraw.Reddit): Instance du client Reddit utilisée pour interroger les subreddits.
            channel (discord.TextChannel): Canal Discord dans lequel les contenus seront publiés.
            bot_user (discord.ClientUser): Représente le bot Discord, utilisé pour filtrer les messages déjà envoyés.
    """  # noqa: E501

    def __init__(
        self,
        reddit: asyncpraw.Reddit,
        channel: discord.TextChannel,
        bot_user: discord.ClientUser,
    ) -> None:
        """
        Initialise un gestionnaire de publication Reddit vers Discord.

        Args:
            reddit (asyncpraw.Reddit): Instance du client Reddit utilisée pour interroger les subreddits.
            channel (discord.TextChannel): Canal Discord dans lequel les contenus seront publiés.
            bot_user (discord.ClientUser): Représente le bot Discord, utilisé pour filtrer les messages déjà envoyés.
        """  # noqa: E501
        self.reddit: asyncpraw.Reddit = reddit
        self.channel: discord.TextChannel = channel
        self.bot_user: discord.ClientUser = bot_user
        self.last_bot_messages: set[str] = set()

    async def fetch_recent_image_urls(self, limit: int = 50) -> set[str]:
        """
        Récupère les URLs des derniers messages envoyés par le bot dans le canal Discord.

        Args:
            limit (int): Nombre de messages à analyser.

        Returns:
            set[str]: Ensemble des URLs d'images déjà postées.
        """
        messages = await fetch_history(self.channel, limit=limit)  # depuis tools.py
        return {
            msg.content
            for msg in messages
            if msg.author == self.bot_user and msg.content.startswith("http")
        }

    async def process_subreddit(self, sub: str) -> None:
        """
        Récupère les nouveaux posts d'un subreddit et les envoie dans le canal Discord si non déjà publiés.

        Args:
            sub (str): Le nom du subreddit à traiter.
        """  # noqa: E501
        try:
            self.last_bot_messages = await self.fetch_recent_image_urls(limit=500)
            submissions = await fetch_new_submissions(self.reddit, sub, limit=10)

            for sub_object in submissions:
                try:
                    if sub_object.image_url not in self.last_bot_messages and sub_object.is_younger(
                        hours=3
                    ):
                        embed = sub_object.to_embed()
                        await self.channel.send(embed=embed)
                        await self.channel.send(sub_object.image_url)
                    else:
                        logger.info("Déjà posté récemment, on skip : %s", sub_object.image_url)
                except RedditException as err:
                    logger.warning("Erreur sur le post '%s' : %s", sub_object.title, err)
        except Exception as e:
            logger.error(f"Erreur lors du traitement du subreddit {sub} : {e}")
