"""Lemonde -> PDF cog."""

import asyncio
import logging
import os
from typing import Literal

import discord
from discord import Interaction, app_commands  # noqa: F401
from discord.ext import commands  # noqa: F401
from dotenv import load_dotenv
from lemonde_sl import LeMondeAsync, MyArticle

from utils.decorators import async_retry, dev_command

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# logger.addHandler(logging.StreamHandler())


# Retry
TRIES = 3
DELAY = 2
MAX_DELAY = 10
BACKOFF = 1.2
# JITTER = 0
JITTER = (0, 1)


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

    @dev_command(name="lemonde", description="Télécharge un article du Monde")
    @app_commands.describe(
        url="URL de l'article à télécharger",
        mode="Choisir mobile et/ou dark theme",
    )
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

        # --- CALLBACK POUR LE RETRY ---
        async def retry_callback(attempt, delay, exc):
            await interaction.followup.send(
                f"Tentative {attempt} échouée — nouvel essai dans {delay:.2f}s…",
                delete_after=delay + 1.9,
            )

        # --- FONCTION UTILITAIRE AVEC RETRY ---
        @async_retry(
            tries=TRIES,
            delay=DELAY,
            max_delay=MAX_DELAY,
            backoff=BACKOFF,
            jitter=JITTER,
            exceptions=(asyncio.exceptions.TimeoutError,),
            on_retry=retry_callback,
        )
        async def retry_get_article(url, mobile, dark_mode):
            return await get_article(url=url, mobile=mobile, dark_mode=dark_mode)

        # --- PARAMÈTRES ---
        mobile = "Mobile" in mode
        dark_mode = "Dark" in mode

        await interaction.response.defer(ephemeral=False)

        logger.info(
            f"Commande /lemonde appelée avec url={url}, mobile={mobile}, dark_mode={dark_mode}"
        )

        await interaction.followup.send(
            f"📄 Article: {url}\n📱 Mobile: {mobile}\n🌙 Mode sombre: {dark_mode}"
        )

        msg_wait = await interaction.followup.send("⏳ Traitement en cours…")

        # --- APPEL AVEC RETRY ---
        try:
            my_article: MyArticle = await retry_get_article(
                url=url, mobile=mobile, dark_mode=dark_mode
            )
            logger.info("PDF généré avec succès")
        except Exception as exc:
            logger.error(f"Erreur fatale: {exc}")
            await interaction.followup.send(
                "❌ Impossible de récupérer l’article après plusieurs tentatives."
            )
            await msg_wait.delete()
            return

        # --- ENVOI DU PDF ---
        try:
            await interaction.followup.send(file=discord.File(my_article.path))
            if my_article.has_warning:
                await interaction.followup.send(my_article.warning)
            os.remove(my_article.path)
        except (TypeError, FileNotFoundError):
            await interaction.followup.send("Echec de la commande. Réessayez peut-être.")
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

    # URL = "https://www.lemonde.fr/international/article/2024/10/03/face-a-l-iran-la-france-se-range-derriere-israel_6342763_3210.html"
    URL = "https://www.lemonde.fr/societe/article/2024/10/05/proces-des-viols-de-mazan-le-huis-clos-leve-les-accuses-maintiennent-leur-version-apres-le-visionnage-des-videos_6344040_3224.html"
    # URL = "https://www.lemonde.fr/les-decodeurs/article/2025/09/25/condamnation-de-nicolas-sarkozy-la-chronologie-complete-de-l-affaire-du-financement-libyen_6482596_4355771.html"
    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        asyncio.run(get_article(URL, mobile=True, dark_mode=True))
    except OSError as e:
        logger.error("Erreur OSError")
        logger.error(e)
