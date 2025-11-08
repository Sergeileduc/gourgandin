from dataclasses import dataclass, field
import logging
from typing import Optional

from asyncpraw.models import Submission
import discord

logger = logging.getLogger(__name__)


@dataclass
class RedditSubmissionInfo:
    submission: Submission
    post_url: str = field(init=False)
    subreddit_name: str = field(init=False)
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
