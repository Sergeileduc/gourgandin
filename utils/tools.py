"""File for some tools."""

import logging
import backoff
import discord
import aiohttp  # asynchronous lib for going on internet
from requests_html import AsyncHTMLSession

from bs4 import BeautifulSoup
from discord.utils import find as disc_find

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
    return BeautifulSoup(text, 'html.parser')


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
