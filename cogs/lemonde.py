"""Lemonde -> PDF cog."""
import asyncio
import logging
import os
import random

import aiohttp
import discord
import pdfkit
from bs4 import BeautifulSoup, Tag
from discord.ext import commands
# from reretry import retry

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# logger.addHandler(logging.StreamHandler())

LOGIN_URL = "https://secure.lemonde.fr/sfuser/connexion"
options = {
    'page-size': 'A4',
    'margin-top': '20mm',
    'margin-right': '20mm',
    'margin-bottom': '20mm',
    'margin-left': '20mm',
    'encoding': "UTF-8",
    'no-outline': None,
    'custom-header': [
        ('Accept-Encoding', 'gzip')
    ],
    "enable-local-file-access": "",
    }

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36',
    }


# Retry
TRIES = 10
DELAY = 2
MAX_DELAY = None
BACKOFF = 1.2
# JITTER = 0
JITTER = (0, 1)


def _new_delay(max_delay, backoff, jitter, delay):
    delay *= backoff
    delay += random.uniform(*jitter) if isinstance(jitter, tuple) else jitter

    if max_delay is not None:
        delay = min(delay, max_delay)

    return delay


def select_tag(soup: BeautifulSoup, selector: str) -> dict:
    """Select tag in soup and return dict (name:value)."""
    items = soup.select(selector)
    return {i['name']: i['value'] for i in items if i.has_attr('name') if i.has_attr('value')}


def remove_bloasts(article: Tag):
    "Remove some bloats in the article soup."
    css = [
        ".meta__social",
        "ul.breadcrumb",
        "section.article__reactions",
        "section.friend",
        "section.article__siblings",
        "aside.aside__iso.old__aside",
        "section.inread",
    ]
    for c in css:
        try:
            list_elements = article.select(c)
            for elem in list_elements:
                elem.decompose()  # remove some bloats
                logger.debug("Element %s decomposed", c)
        except AttributeError:
            logger.info("FAILS to remove %s bloat in the article. Pass.", c)


def fix_images_urls(article: BeautifulSoup) -> None:
    """Fixes image URLs in the provided article by updating the 'src' attribute.

    This function scans the article for image tags and updates their 'src'
    attributes based on the 'data-srcset' attribute. It ensures that the images
    are correctly referenced for display.

    Args:
        article (BeautifulSoup): The BeautifulSoup object representing
        the article from which to fix image URLs.

    Returns:
        None
    """

    imgs = article.select("img")
    for im in imgs:
        if im.has_attr("data-srcset"):
            srcset = im["data-srcset"]
            tmpsrc = srcset.split(",")
            for tmp in tmpsrc:
                if "664w" in tmp or "1x" in tmp:
                    url_im = tmp.strip().split(" ")[0]
                    im["src"] = url_im


# @retry(asyncio.exceptions.TimeoutError, tries=10, delay=2, backoff=1.2, jitter=(0, 1))
async def get_article(url: str) -> str:
    """Get the article from the URL

    Args:
        url (str): url of article to be fetched

    Returns:
        str: path to the PDF file
    """
    session = aiohttp.ClientSession(headers=headers)
    # Login
    r = await session.get(LOGIN_URL)
    soup = BeautifulSoup(await r.text(), "html.parser")
    form = soup.select_one('form[method="post"]')
    payload = select_tag(form, "input")
    email = os.getenv("LEMONDE_EMAIL")
    payload['email'] = email
    payload['password'] = os.getenv("LEMONDE_PASSWD")
    rp = await session.post(LOGIN_URL, data=payload)
    if rp.status != 200 or email not in await rp.text():
        raise ValueError("Wrong login")
    else:
        logger.info("Login was ok")
    await asyncio.sleep(random.uniform(2.0, 3.0))

    html = None
    # Fetch article and print in PDF
    try:
        r = await session.get(url, headers=headers, timeout=6)
        logger.info("status : %s", r.status)
        html = await r.text()
        logger.info("Get was ok")
    except asyncio.exceptions.TimeoutError:
        logger.warning("Timeout !")
        raise
    finally:
        await session.close()

    if html:
        logger.info("Ok, doing some magic on HTML")
        soup = BeautifulSoup(html, 'html.parser')
        article = soup.select_one("main > .article--content")
        # article = soup.select_one("section.zone--article")
        # article = soup.select_one(".zone.zone--article")
        remove_bloasts(article)
        fix_images_urls(article)

        full_name = url.rsplit('/', 1)[-1]
        out_file = f"{os.path.splitext(full_name)[0]}.pdf"
        logger.info("Ok, making the pdf now.")
        pdfkit.from_string(str(article), out_file, options=options)
        logger.info("Returning file")
        return out_file
    return None


class LeMonde(commands.Cog):
    """LeMonde commands"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command()
    # @commands.command()
    async def lemonde(self, ctx: commands.Context, url: str):
        "Download an article from Lemonde.fr"
        # Retry
        _tries, _delay = TRIES, DELAY

        await ctx.defer(ephemeral=False)

        # While loop to retry fetching article, in case of Timeout errors
        while _tries:
            try:
                out_file = await get_article(url)
                logger.info("out file ok")
                break
            except asyncio.exceptions.TimeoutError:
                logger.warning("Timeout in retry code !!!")
                _tries -= 1
                logger.warning("Tries left = %d", _tries)

                error_message = ("Erreur : Timeout. "
                                 f"Tentative {TRIES - _tries}/{TRIES} échec - "
                                 f"Nouvel essai dans {_delay:.2f} secondes...")
                delete_after = _delay + 1.9
                await ctx.channel.send(error_message, delete_after=delete_after)
                if not _tries:
                    raise

                await asyncio.sleep(_delay)

                _delay = _new_delay(MAX_DELAY, BACKOFF, JITTER, _delay)
        # End of retry While loop

        try:
            await ctx.send(content=url)
            await ctx.send(file=discord.File(out_file))
            os.remove(out_file)
        except (TypeError, FileNotFoundError):
            await ctx.send("Echec de la commande. Réessayez, peut-être ?")
        finally:
            logger.info("------------------")


async def setup(bot):
    """
    Sets up the LeMonde cog for the provided Discord bot instance.

    This asynchronous function adds the LeMonde cog to the bot and logs a message
    indicating the successful addition of the cog.

    Args:
        bot: The Discord bot instance to which the cog will be added.

    Returns:
        None
    """
    await bot.add_cog(LeMonde(bot))
    logger.info("lemonde cog added")


# TESTING
if __name__ == "__main__":
    # Testing lemonde pdf
    import platform
    from dotenv import load_dotenv
    # Parse a .env file and then load all the variables found as environment variables.
    load_dotenv()

    logging.basicConfig(level=logging.DEBUG)

    URL = "https://www.lemonde.fr/international/article/2024/10/03/face-a-l-iran-la-france-se-range-derriere-israel_6342763_3210.html"
    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

        asyncio.run(get_article(URL))
