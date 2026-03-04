import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from asyncpraw.models import Submission


def canonical_id_from_url(url: str) -> str | None:
    """Extract the canonical Reddit ID from a submission URL.
    Example : "https://www.reddit.com/gallery/1rht5ue" -> 1rht5ue
    """
    m = re.search(r"/([a-z0-9]{6,8})/?$", url)
    return m.group(1) if m else None


async def resolve_submission(submission: "Submission") -> "Submission":
    """Retourne la vraie submission (ID canonique), si l'ID API est un alias."""
    await submission.load()

    canonical_id = canonical_id_from_url(submission.url)
    if canonical_id and canonical_id != submission.id:
        # recharge la vraie submission
        real = await submission._reddit.submission(id=canonical_id)
        await real.load()
        return real

    return submission


if __name__ == "__main__":
    url = "https://www.reddit.com/gallery/1rht5ue"

    print(canonical_id_from_url(url))
