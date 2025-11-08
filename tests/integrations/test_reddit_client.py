# TODO : asyncPraw, etc...

# import pytest
# from reddit.reddit_client import RedditClient
# from reddit.reddit_types import RedditSubmissionInfo


# @pytest.mark.asyncio
# async def test_fetch_10_submissions_from_real_subreddit():
#     # Initialise ton client avec ton token (via env ou fichier local sécurisé)
#     client = RedditClient(token="TON_TOKEN_REDDIT")

#     # Appelle un vrai subreddit
#     submissions = await client.fetch_submissions("pics", limit=10)

#     # Vérifie qu'on a bien 10 résultats
#     assert len(submissions) == 10

#     # Vérifie que chaque élément est bien du bon type
#     for submission in submissions:
#         assert isinstance(submission, RedditSubmissionInfo)
#         assert submission.url.startswith("http")
#         assert submission.title
