import asyncio
import os
import random
from collections.abc import Awaitable, Callable
from functools import wraps  # noqa: F401

from discord import Object, app_commands

DEV_MODE = os.getenv("DEV_MODE", "").strip().lower() in ("1", "true", "yes", "on")
DEV_GUILD_ID = int(os.getenv("DEV_GUILD_ID", "0"))


def dev_command(**kwargs):
    """
    décorateur `@dev_command`, conçu pour faciliter l'enregistrement conditionnel
    des commandes slash (`@app_commands.command`) dans un environnement de développement ou de production.

    Fonctionnalités :
    - Permet d'enregistrer une commande slash dans une guild spécifique en mode développement.
    - En mode production, la commande est enregistrée globalement.
    - Ajoute dynamiquement un attribut `_dev_guild` à la commande, utilisé par `BaseSlashCog` pour l'enregistrement.

    Utilisation :
    - À utiliser à la place de `@app_commands.command` dans les cogs héritant de `BaseSlashCog`.
    - Le mode est contrôlé par la constante `DEV_MODE` (True pour dev, False pour prod).
    - L'ID de la guild de test est défini par `DEV_GUILD_ID`.

    Exemple :
        @dev_command(name="ping", description="Répond pong")
        async def ping(self, interaction: discord.Interaction):
            await interaction.response.send_message("Pong!")

    Auteur : Sergeileduc
    """  # noqa: E501

    def wrapper(func):
        # Crée la commande comme d’habitude
        cmd = app_commands.command()(func)

        # Injecte l’attribut _dev_guild utilisé par BaseSlashCog
        cmd._dev_guild = Object(id=DEV_GUILD_ID)
        return cmd

    return wrapper


def async_retry(
    tries: int,
    delay: float,
    max_delay: float,
    backoff: float,
    jitter: tuple[float, float],
    exceptions: tuple[type[BaseException], ...],
    on_retry: Callable[[int, float, Exception], Awaitable[None]] | None = None,
):
    """
    Retry decorator for asynchronous functions with exponential backoff and optional jitter.

    This decorator retries an async function when it raises one of the specified
    exceptions. Between each attempt, it waits for a delay that increases using
    an exponential backoff strategy, optionally combined with jitter. An optional
    asynchronous callback can be executed on each retry attempt (e.g., logging or
    sending a notification).

    Args:
        tries (int):
            Maximum number of attempts before giving up.
        delay (float):
            Initial delay (in seconds) before the first retry.
        max_delay (float):
            Maximum allowed delay between retries.
        backoff (float):
            Multiplicative factor applied to the delay after each attempt.
        jitter (tuple (float, float)):
            Additional randomization factor applied to the delay to avoid thundering herd.
        exceptions (tuple[type[BaseException], ...]):
            Exception types that should trigger a retry.
        on_retry (Callable[[int, float, Exception], Awaitable[None]] | None):
            Optional async callback executed on each retry. Receives:
            - attempt number (starting at 1),
            - current delay,
            - the caught exception.

    Returns:
        Callable:
            A wrapped asynchronous function with retry behavior.

    Raises:
        Exception:
            Re-raises the last caught exception if all retry attempts fail.
    """

    def decorator(func):
        async def wrapper(*args, **kwargs):
            _tries = tries
            _delay = delay

            while _tries > 0:
                try:
                    return await func(*args, **kwargs)

                except exceptions as exc:
                    _tries -= 1

                    if on_retry:
                        await on_retry(tries - _tries, _delay, exc)

                    if _tries == 0:
                        raise

                    await asyncio.sleep(_delay)

                    # backoff + jitter
                    j_min, j_max = jitter
                    j = random.uniform(j_min, j_max)
                    _delay = min(max_delay, _delay * backoff + j * _delay)

        return wrapper

    return decorator
