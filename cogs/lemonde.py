"""Lemonde -> PDF cog."""
import asyncio
import logging
import os
import random
from typing import Literal

import discord
from discord import app_commands
from discord.ext import commands

# from reretry import retry
from dotenv import load_dotenv
from lemonde_sl import LeMondeAsync, MyArticle

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# logger.addHandler(logging.StreamHandler())

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


async def get_article(url: str, mobile: bool, dark_mode: bool) -> MyArticle:
    """
    Fetch and generate a PDF version of a Le Monde article using the library's
    asynchronous client.

    This helper function encapsulates the interaction with ``LeMondeAsync`` so
    that the Discord bot does not need to manage the client lifecycle, login
    details, or PDF generation logic directly. Centralizing this logic keeps the
    bot code clean, makes error handling consistent, and allows the underlying
    implementation to evolve without requiring changes in the bot.

    Args:
        url (str): The URL of the Le Monde article to fetch.
        mobile (bool): Whether to render the article using the mobile layout
            (A6 format, reduced margins).
        dark_mode (bool): Whether to apply the dark theme to the generated PDF.

    Returns:
        MyArticle: A structured result containing:
            - ``path``: Path to the generated PDF file.
            - ``success``: Whether the PDF was generated without fatal errors.
            - ``warning``: Optional warning message (e.g., multimedia removed).

    Notes:
        This function exists to decouple the bot from the internal details of
        the Le Monde scraping and PDF generation pipeline. It provides a stable
        interface for the bot, while allowing the library to change its internal
        behavior (authentication, HTML parsing, fallback strategies, etc.)
        without requiring modifications in the bot code.
    """

    # Load environment variables (idempotent)
    load_dotenv()

    EMAIL = os.getenv("LM_SL_EMAIL")
    PASSWORD = os.getenv("LM_SL_PASSWD")

    if not EMAIL or not PASSWORD:
        raise RuntimeError("Missing LM_SL_EMAIL or LM_SL_PASSWD in environment")

    async with LeMondeAsync() as lm:
        return await lm.fetch_pdf(
            url=url,
            email=EMAIL,
            password=PASSWORD,
            mobile=mobile,
            dark=dark_mode,
        )



class LeMonde(commands.Cog):
    """LeMonde commands"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="lemonde", description="Télécharge un article en PDF")
    async def lemonde(
        self,
        interaction: discord.Interaction,
        url: str,
        mode: Literal[
            "Normal Clair", "Normal Dark", "Mobile Clair", "Mobile Dark"
        ] = "Normal Clair",
    ) -> None:
        """
        Télécharge un article depuis Lemonde.fr et l'affiche dans Discord.

        Args:
            interaction(discord.Interaction): L'interaction Discord.
            url (str): Lien vers l'article.
            mobile (Literal["Oui", "Non"]): Mode mobile.
            dark_mode (Literal["Oui", "Non"]): Mode sombre.

        Comportement :
            - Affiche les paramètres reçus dans un message de suivi.
            - Tente de récupérer l'article avec plusieurs essais en cas de timeout.
            - Utilise `to_bool()` pour convertir les paramètres en booléens.
        """

        mobile: bool = "Mobile" in mode
        dark_mode: bool = "Dark" in mode

        await interaction.response.defer(ephemeral=False)

        # Log pour debug
        logger.info(
            f"Commande /lemonde appelée avec url={url}, mobile={mobile}, dark_mode={dark_mode}"
        )
        await interaction.followup.send(
            f"📄 Article: {url}\n📱 Mobile: {mobile}\n🌙 Mode sombre: {dark_mode}"
        )

        # Retry
        _tries, _delay = TRIES, DELAY

        msg_wait = await interaction.followup.send("⏳ Traitement en cours…", ephemeral=False)
        # While loop to retry fetching article, in case of Timeout errors
        while _tries:
            try:
                my_article: MyArticle = await get_article(
                    url=url, mobile=mobile, dark_mode=dark_mode
                )
                logger.info("out file ok")
                break
            except asyncio.exceptions.TimeoutError:
                logger.warning("Timeout in retry code !!!")
                _tries -= 1
                logger.warning("Tries left = %d", _tries)

                error_message = (
                    "Erreur : Timeout. "
                    f"Tentative {TRIES - _tries}/{TRIES} échec - "
                    f"Nouvel essai dans {_delay:.2f} secondes..."
                )
                delete_after = _delay + 1.9
                await interaction.followup.send(error_message, delete_after=delete_after)
                if not _tries:
                    raise

                await asyncio.sleep(_delay)

                _delay = _new_delay(MAX_DELAY, BACKOFF, JITTER, _delay)
        # End of retry While loop

        try:
            # await interaction.followup.send(content=url)
            await interaction.followup.send(file=discord.File(my_article.path))
            if my_article.has_warning:
                await interaction.followup.send(my_article.warning)
            os.remove(my_article.path)
        except (TypeError, FileNotFoundError):
            await interaction.followup.send("Echec de la commande. Réessayez, peut-être ?")
        finally:
            await msg_wait.delete()
            logger.info("------------------")


async def setup(bot) -> None:
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
