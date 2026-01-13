"""
reddit_client.py

Ce module gère l'interaction avec l'API Reddit via asyncpraw.
Il fournit :
- une fonction pour initialiser le client Reddit
- une fonction pour récupérer les dernières soumissions d'un subreddit
- une transformation des objets asyncpraw en RedditSubmissionInfo

Utilisé par reddit_poster.py pour alimenter les embeds Discord.
"""

import logging
import os

import asyncpraw
from dotenv import load_dotenv

from .reddit_models import RedditSubmissionInfo

logger = logging.getLogger(__name__)
load_dotenv()


def get_reddit_client() -> asyncpraw.Reddit:
    """
    Initialise et retourne un client Reddit asyncpraw.

    Les identifiants sont lus depuis les variables d'environnement chargées via dotenv.
    """
    return asyncpraw.Reddit(
        client_id=os.environ["REDDIT_ID"],
        client_secret=os.environ["REDDIT_SECRET"],
        user_agent=os.environ["REDDIT_AGENT"]
    )


async def fetch_new_submissions(
    reddit: asyncpraw.Reddit,
    subreddit_name: str,
    limit: int = 10
) -> list[RedditSubmissionInfo]:
    """
    Récupère les dernières soumissions d'un subreddit donné, en filtrant les posts stickés ou supprimés,
    et les transforme en objets RedditSubmissionInfo.

    Args:
        reddit (asyncpraw.Reddit): Instance du client Reddit déjà initialisée.
        subreddit_name (str): Nom du subreddit à interroger.
        limit (int, optional): Nombre maximum de soumissions à récupérer. Par défaut à 10.

    Returns:
        list[RedditSubmissionInfo]: Liste d'objets représentant les soumissions valides.
    """  # noqa: E501
    subreddit = await reddit.subreddit(subreddit_name, fetch=True)
    logger.info("Fetching subreddit: %s", subreddit_name)

    submissions = []
    async for submission in subreddit.new(limit=limit):
        if submission.stickied or submission.removed_by_category == "deleted":
            continue

        info = RedditSubmissionInfo(submission=submission)
        submissions.append(info)

    return submissions
