import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import discord
from asyncpraw.models import Submission

logger = logging.getLogger(__name__)

PREFIXES: list[str] = [
    "Nines from the Mild side",
]


@dataclass
class RedditSubmissionInfo:
    submission: Submission
    post_url: str = field(init=False)
    subreddit_name: str = field(init=False)
    title: str = field(init=False)
    formated_title: str = field(init=False)
    author: str = field(init=False)
    is_album: bool = field(init=False)
    image_count: int = field(init=False)
    image_url: str | None = field(init=False)
    created_at: datetime = field(init=False)

    def __post_init__(self):
        self.post_url = self.submission.url
        self.subreddit_name = self.submission.subreddit.display_name
        self.title = self.submission.title
        self.author = str(self.submission.author)
        self.is_album = hasattr(self.submission, "media_metadata") and bool(
            self.submission.media_metadata
        )
        self.image_url = None
        self.image_count = 0
        self.created_at = datetime.fromtimestamp(self.submission.created_utc, tz=UTC)
        logger.info("\t🧵 self.post_url : %s", self.post_url)

        if self.is_album:
            logger.info("\t  📔 that's an album %s", self.post_url)
            logger.info("\t  📔 getting the first image for %s", self.submission)
            self._extract_album_info()
        elif (
            self.submission.url.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp"))
            or "redgifs" in self.submission.url
        ):
            self.image_url = self.submission.url
            self.image_count = 1
            logger.info("\t  🍑 standard submission with one pic : %s", self.submission)
        else:
            logger.error(
                "something bad happened with picture for submission %s, we got this url %s",
                self.post_url,
                self.image_url,
            )  # noqa: E501
            print("submission URL : ", self.submission.url)
            print("submission ID : ", self.submission.id)
            raise RedditException(
                "Impossible de trouver du contenu",
                submission_id=self.submission.id,
                url=self.post_url,
            )
        logger.info("\t  🖼️ self.image_url : %s", self.image_url)

    def _extract_album_info(self):
        try:
            items = self.submission.gallery_data.get("items", [])
            if not isinstance(items, list) or not items:
                raise RedditException(
                    "Aucune image trouvée dans l'album",
                    submission_id=self.submission.id,
                    url=self.post_url,
                )

            first_media_id = items[0].get("media_id")
            if not first_media_id:
                raise RedditException(
                    "media_id manquant dans le premier item",
                    submission_id=self.submission.id,
                    url=self.post_url,
                )

            image_info = self.submission.media_metadata.get(first_media_id, {})
            self.image_url = image_info.get("s", {}).get("u")
            logger.warning("\t  🖼️ Image found in album : %s", self.image_url)
            if not self.image_url:
                raise RedditException(
                    "URL de l'image introuvable dans les métadonnées",
                    submission_id=self.submission.id,
                    url=self.post_url,
                )

            self.image_count = len(items)
        except (AttributeError, TypeError, KeyError) as e:
            raise RedditException(
                f"Erreur lors de l'extraction des images : {e}",
                submission_id=self.submission.id,
                url=self.post_url,
            ) from e

    @staticmethod
    def _extract_suffix_regex(s: str, prefix: str) -> str:
        """Extract suffix

        Args:
            s (str): string to process
            prefix (str): Prefix to delete.

        Returns:
            str: clean string without suffix

        Example:
            s = "Nines from the Mild side - Marli"
            print(extract_suffix_regex(s, "Nines from the Mild side"))
            # → Marli
        """
        pattern = rf"^{re.escape(prefix)}\s*-\s*(.+)$"
        m = re.match(pattern, s)
        return m.group(1) if m else s

    def _clean_title(self) -> None:
        """Make embed title.

        Strip prefixes, and limit to 256 chars for Discord.
        """
        for prefix in PREFIXES:
            new_title = self._extract_suffix_regex(self.title, prefix)
        self.formated_title = new_title[:256]

    def to_embed(self) -> discord.Embed:
        self._clean_title()
        embed = discord.Embed(
            title=self.formated_title,
            description=self.subreddit_name,
            url=f"https://www.reddit.com{self.submission.permalink}",
        )
        if self.is_album:
            embed.set_footer(
                text=f"Album de {self.image_count} images",
                icon_url="https://images.emojiterra.com/twitter/v13.1/512px/1f4d6.png",
            )
        # if self.image_url:
        #     embed.set_image(url=self.image_url)
        # embed.set_footer(text=f"Posté par u/{self.author}")
        return embed

    def is_younger(self, days: int = 1, hours: int = 0) -> bool:
        """Retourne True si le post est plus récent que la durée donnée."""
        delta = timedelta(days=days, hours=hours)
        return datetime.now(UTC) - self.created_at < delta


class RedditException(Exception):
    def __init__(self, message: str, submission_id: str | None = None, url: str | None = None):
        self.submission_id = submission_id
        super().__init__(
            f"[RedditException] {message} (ID: {submission_id})\n{url}"
            if (submission_id and url)
            else message
        )


if __name__ == "__main__":
    # s = "Nines from the Mild side - Marli"
    # print(RedditSubmissionInfo._extract_suffix_regex(s, "Nines from the Mild side"))
    # # → Marli

    import asyncio
    import os

    import asyncpraw
    from dotenv import load_dotenv

    load_dotenv()
    REDDIT_ID = os.getenv("REDDIT_ID")
    REDDIT_SECRET = os.getenv("REDDIT_SECRET")
    REDDIT_AGENT = os.getenv("REDDIT_AGENT")

    async def main():
        reddit = asyncpraw.Reddit(
            client_id=REDDIT_ID, client_secret=REDDIT_SECRET, user_agent=REDDIT_AGENT
        )
        ID = "1rxb6re"

        print(f"on essaye avec l'ID : {ID}")
        submission = await reddit.submission(id=ID)
        await submission.load()

        info = RedditSubmissionInfo(submission=submission)

        info._clean_title()
        print(info.formated_title)

        print("-----------------")
        await reddit.close()

    asyncio.run(main())
