"""File for some tools."""

import aiohttp
import requests
import logging
from typing import Optional

import backoff
import discord
from discord.ext import commands
from requests_html import AsyncHTMLSession

from bs4 import BeautifulSoup
from discord.utils import find as disc_find

try:
    from requests_html import HTMLSession
    HAS_REQUESTS_HTML = True
except ImportError:
    HAS_REQUESTS_HTML = False


logger = logging.getLogger(__name__)

headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}  # noqa:E501


def string_is_int(string: str) -> bool:  # pragma: no cover
    """Return if 'string' is an int or not (bool)."""
    try:
        int(string)
        return True
    except ValueError:
        return False


async def get_soup_lxml(url: str) -> BeautifulSoup:
    """Return a BeautifulSoup soup from given url, Parser is lxml.

    Args:
        url (str): url

    Returns:
        BeautifulSoup: soup

    """
    # get HTML page with async GET request
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=3, ssl=False, headers=headers) as resp:
            text = await resp.text()
        await session.close()
    return BeautifulSoup(text, 'lxml')


async def get_soup_html(url: str) -> BeautifulSoup:
    """Return a BeautifulSoup soup from given url, Parser is html.parser.

    Args:
        url (str): url

    Returns:
        BeautifulSoup: soup

    """
    # get HTML page with async GET request
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=3, ssl=False) as resp:
            text = await resp.text()
        await session.close()
    # BeautifulSoup will transform raw HTML in a tree easy to parse
    return BeautifulSoup(text, features='html.parser')


def args_separator_for_log_function(guild, args):
    """Check the args if there are user, channel and command."""
    commands = ['kick', 'clear', 'ban']
    [user, command, channel] = [None, None, None]  # They are defaulted to None, if any of them is specified, it will be changed  # noqa:E501
    for word in args:
        # if disc_get(guild.members, name=word) is not None: # if word is a member of the guild  # noqa:E501
        if disc_find(lambda m: m.name.lower() == word.lower(), guild.members) is not None:  # same, but case insensitive  # noqa:E501
            user = word.lower()
        # elif disc_get(guild.text_channels, name=word) is not None: # if word is a channel of the guild  # noqa:E501
        elif disc_find(lambda t: t.name.lower() == word.lower(), guild.text_channels) is not None:  # same, but case insensitive  # noqa:E501
            channel = word.lower()
        elif word in commands:  # if word is a command
            command = word.lower()
    # variables not specified in the args are defaulted to None
    return [user, command, channel]


async def get_soup_xml(url: str) -> BeautifulSoup:
    """Return a BeautifulSoup soup from given url, Parser is xml.

    Args:
        url (str): url

    Returns:
        BeautifulSoup: soup

    """
    asession = AsyncHTMLSession()
    r = await asession.get(url, headers=headers, timeout=3)
    await asession.close()
    return BeautifulSoup(r.text, 'xml')


# this function can be reused. it's not a bug if we define it in get_last_bot_messages again.
# it's because of the decorator...
@backoff.on_exception(backoff.expo, discord.DiscordServerError, max_tries=5)
async def fetch_history(
    channel: discord.TextChannel,
    limit: int = 500
) -> list[discord.Message]:
    """
    Récupère l'historique des messages d'un canal Discord avec stratégie de retry en cas d'erreur serveur.

    Cette fonction interroge l'historique d'un canal Discord et retourne les derniers messages,
    jusqu'à une limite définie. Elle utilise un décorateur `backoff` pour réessayer automatiquement
    en cas d'erreur `DiscordServerError`, avec un délai exponentiel entre les tentatives.

    Args:
        channel (discord.TextChannel): Le canal Discord à interroger.
        limit (int, optional): Nombre maximum de messages à récupérer. Par défaut à 500.

    Returns:
        list[discord.Message]: Liste des messages présents dans l'historique du canal.
    """
    return [message async for message in channel.history(limit=limit)]


# again : not a bug if fetch_history is defined inside.
async def get_last_bot_messages(
    channel: discord.TextChannel,
    bot_user: discord.ClientUser,
    max_tries: int = 5,
    history_limit: int = 500
) -> list[str]:
    """
    Récupère les messages récemment envoyés par le bot dans un canal Discord.

    Cette fonction interroge l'historique d'un canal Discord pour extraire les messages
    envoyés par le bot. Elle utilise une stratégie de retry exponentiel en cas d'erreur
    serveur Discord (503), avec un nombre de tentatives et une profondeur d'historique
    configurables.

    Args:
        channel (discord.TextChannel): Le canal Discord à analyser.
        bot_user (discord.ClientUser): L'utilisateur représentant le bot.
        max_tries (int, optional): Nombre maximum de tentatives en cas d'erreur Discord.
            Par défaut à 5.
        history_limit (int, optional): Nombre maximum de messages à récupérer dans
            l'historique du canal. Par défaut à 500.

    Returns:
        list[str]: Liste des contenus textuels des messages envoyés par le bot.
                   Retourne une liste vide en cas d'échec.
    """
    async def fetch_history() -> list[discord.Message]:
        @backoff.on_exception(backoff.expo, discord.DiscordServerError, max_tries=max_tries)
        async def inner() -> list[discord.Message]:
            return [message async for message in channel.history(limit=history_limit)]
        return await inner()

    try:
        history = await fetch_history()
    except discord.DiscordServerError as e:
        logger.warning(f"Erreur Discord 503 lors de la récupération de l'historique : {e}")
        return []

    return [message.content for message in history if message.author == bot_user]


def get_channel_by_name(bot: commands.Bot, guild_id: int, channel_name: str) -> Optional[discord.TextChannel]:
    """
    Resolve a text channel by its name within a given guild.

    Parameters
    ----------
    bot : commands.Bot
        The Discord bot instance, used to access guilds and channels.
    guild_id : int
        The ID of the guild (server) where the channel should be searched.
    channel_name : str
        The exact name of the text channel to resolve.

    Returns
    -------
    Optional[discord.TextChannel]
        The resolved text channel object if found, otherwise None.

    Notes
    -----
    - This function performs a lookup by channel name, which is explicit and human-readable.
    - If the guild is not yet available (e.g., before on_ready), the function will return None.
    - Prefer using channel IDs for robustness, but this helper is useful for quick testing
      or when channel names are stable and meaningful.
    """
    guild = bot.get_guild(guild_id)
    if guild is None:
        return None
    return discord.utils.get(guild.text_channels, name=channel_name)


def make_soup(
    url: str,
    parser: str = "html.parser",
    timeout: int = 3,
    ssl: bool = True,
    backend: str = "requests"
) -> BeautifulSoup:
    """
    Télécharge le contenu HTML d'une URL en mode synchrone et retourne un objet BeautifulSoup.

    Args:
        url (str): L'URL de la page à récupérer.
        parser (str, optional): Parser utilisé pour analyser le HTML.
            - "html.parser" (par défaut) : parser intégré à Python, rapide et sans dépendance externe.
            - "lxml" : nécessite l'installation de lxml, plus rapide et robuste.
            - "html5lib" : parser fidèle au standard HTML5.
        timeout (int, optional): Timeout en secondes pour la requête (par défaut 3).
        ssl (bool, optional): Active/désactive la vérification SSL (par défaut True).
            ⚠️ Avec requests, `ssl=False` équivaut à `verify=False`.
        backend (str, optional): Choix du backend HTTP.
            - "requests" (par défaut)
            - "requests_html" : exécute aussi le JavaScript (si installé).

    Returns:
        BeautifulSoup: Objet représentant l'arbre DOM de la page.

    Raises:
        requests.exceptions.RequestException: Si la requête échoue (connexion, timeout, etc.).
        requests.exceptions.HTTPError: Si le serveur retourne un code d'erreur HTTP.

    Example:
        >>> soup = make_soup("https://example.com")
        >>> print(soup.title.string)
        'Example Domain'
    """
    if backend == "requests_html" and HAS_REQUESTS_HTML:
        session = HTMLSession()
        resp = session.get(url, timeout=timeout, verify=ssl)
        resp.html.render()
        return BeautifulSoup(resp.html.html, features=parser)
    else:
        resp = requests.get(url, timeout=timeout, verify=ssl)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, features=parser)


async def amake_soup(
    url: str,
    parser: str = "html.parser",
    timeout: int = 3,
    ssl: bool = False,
    backend: str = "aiohttp"
) -> BeautifulSoup:
    """
    Télécharge le contenu HTML d'une URL en mode asynchrone et retourne un objet BeautifulSoup.

    Args:
        url (str): L'URL de la page à récupérer.
        parser (str, optional): Parser utilisé pour analyser le HTML.
            - "html.parser" (par défaut)
            - "lxml"
            - "html5lib"
        timeout (int, optional): Timeout en secondes pour la requête (par défaut 3).
        ssl (bool, optional): Active/désactive la vérification SSL (par défaut False).
            ⚠️ Avec aiohttp, `ssl=False` désactive la vérification des certificats.
        backend (str, optional): Choix du backend HTTP.
            - "aiohttp" (par défaut)
            - "requests_html" : utilise AsyncHTMLSession (si installé).
            - "httpx" : possible extension future.

    Returns:
        BeautifulSoup: Objet représentant l'arbre DOM de la page.

    Raises:
        aiohttp.ClientError: Si la requête échoue (connexion, timeout, etc.).
        aiohttp.ClientResponseError: Si le serveur retourne un code d'erreur HTTP.

    Example:
        >>> soup = await amake_soup("https://example.com")
        >>> print(soup.title.string)
        'Example Domain'
    """
    if backend == "requests_html" and HAS_REQUESTS_HTML:
        session = AsyncHTMLSession()
        resp = await session.get(url, timeout=timeout, verify=ssl)
        await resp.html.arender()
        return BeautifulSoup(resp.html.html, features=parser)

    elif backend == "httpx":
        import httpx
        async with httpx.AsyncClient(timeout=timeout, verify=ssl) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, features=parser)

    else:  # aiohttp par défaut
        timeout_obj = aiohttp.ClientTimeout(total=timeout)
        async with aiohttp.ClientSession(timeout=timeout_obj) as session:
            async with session.get(url, ssl=ssl) as resp:
                resp.raise_for_status()
                text = await resp.text()
                return BeautifulSoup(text, features=parser)


def soup_from_text(text: str, parser: str = "html.parser") -> BeautifulSoup:
    """
    Construit un objet BeautifulSoup directement à partir d'une chaîne HTML.

    Args:
        text (str): Chaîne contenant du HTML brut.
        parser (str, optional): Parser utilisé pour analyser le HTML.
            - "html.parser" (par défaut)
            - "lxml"
            - "html5lib"

    Returns:
        BeautifulSoup: Objet représentant l'arbre DOM du HTML fourni.

    Example:
        >>> html = "<html><head><title>Hello</title></head><body>World</body></html>"
        >>> soup = soup_from_text(html)
        >>> print(soup.title.string)
        'Hello'
    """
    return BeautifulSoup(text, features=parser)
