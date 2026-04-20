"""Awesome Discord Bot."""

import argparse
import asyncio
import logging
import os
import platform

import discord
from discord.ext import commands
from dotenv import load_dotenv

from utils.tools import get_ram_usage_mb

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Parse a .env file and then load all the variables found as environment variables.
load_dotenv()
TOKEN = os.getenv("GOURGANDIN_TOKEN")
try:
    GUILD_ID = int(os.getenv("GUILD_ID"))  # type: ignore[arg-type]
except (ValueError, TypeError):
    logger.error("GUILD_ID in your varenvs or .env must be integer !!!")
# Done


PREFIX: str = "!"
NSFW_BOT_CHANNEL: str = "nsfw-bot"
NSFW_MANUAL_CHANNEL: str = "nsfw-manuel"

# --debug option
parser = argparse.ArgumentParser()
parser.add_argument("-d", "--debug", help="change prefix to '?'", action="store_true")
args = parser.parse_args()
if args.debug:
    logger.info("You are in debug mode.")
    logger.info("Prefix is now '?'")
    PREFIX = "?"
    NSFW_BOT_CHANNEL = "test-bot"
    logging.basicConfig(level=logging.DEBUG)


# parameters for the bot
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(
    command_prefix=PREFIX,
    help_command=None,
    description=None,
    case_insensitive=True,
    intents=intents,
)

cogs_ext_list = [
    "cogs.bonjourmadame",
    "cogs.misc",
    "cogs.lemonde",
    "cogs.code",
    #  "cogs.jv",
    "cogs.redditbabes.redditbabes",
    "cogs.youtube",
    "cogs.nsfwapi",
]


@bot.event
async def on_ready():
    """Log in Discord."""
    logger.info("🔐 Logged in as")
    logger.info("🔐 %s", bot.user.name)
    logger.info("🔐 %s", bot.user.id)

    await bot.tree.sync()
    logger.info("Cogs loaded and channels set.")
    before = get_ram_usage_mb()
    logger.info("RAM after on_ready: %.1f MB", before)


@bot.event
async def setup_hook():
    """A coroutine to be called to setup the bot.

    To perform asynchronous setup after the bot is logged in but before
    it has connected to the Websocket, overwrite this coroutine.

    This is only called once, in `login`, and will be called before
    any events are dispatched, making it a better solution than doing such
    setup in the `~discord.on_ready` event.

    Warning :
    Since this is called *before* the websocket connection is made therefore
    anything that waits for the websocket will deadlock, this includes things
    like :meth:`wait_for` and :meth:`wait_until_ready`.
    """
    logger.info("Setup_hook !!!")
    for ext in cogs_ext_list:
        await bot.load_extension(ext)


if __name__ == "__main__":
    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    logger.info("New bot with discord.py version %s", discord.__version__)
    if TOKEN:
        bot.run(TOKEN)
    else:
        logger.error("Please give a valid GOURGANDIN_TOKEN in your varenvs or .env file")
