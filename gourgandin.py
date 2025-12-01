#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""Awesome Discord Bot."""
import argparse
import asyncio
import logging
import os
import platform

import discord
from discord.ext import commands
from dotenv import load_dotenv


# Parse a .env file and then load all the variables found as environment variables.
load_dotenv()
TOKEN: str = os.getenv("GOURGANDIN_TOKEN")
GUILD_ID: int = int(os.getenv("GUILD_ID"))
# Done

# Logging
logging.basicConfig(level=logging.INFO)

PREFIX: str = '!'
NSFW_BOT_CHANNEL: str = "nsfw-bot"
NSFW_MANUAL_CHANNEL: str = "nsfw-manuel"

# --debug option
parser = argparse.ArgumentParser()
parser.add_argument("-d", "--debug",
                    help="change prefix to '?'", action="store_true")
args = parser.parse_args()
if args.debug:
    logging.info("You are in debug mode.")
    logging.info("Prefix is now '?'")
    PREFIX = '?'
    NSFW_BOT_CHANNEL: str = "test-bot"
    logging.basicConfig(level=logging.DEBUG)


# parameters for the bot
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix=PREFIX, help_command=None,
                   description=None, case_insensitive=True, intents=intents)

cogs_ext_list = ["cogs.bonjourmadame",
                 "cogs.misc",
                 "cogs.lemonde",
                 "cogs.code",
                #  "cogs.jv",
                 "cogs.redditbabes.redditbabes",
                 "cogs.youtube",
                 "cogs.nsfwapi",
                 ]

# TODO : c'est un peu moche, setup_hook c'est quand même mieux que de charger dans on_ready,
# mais on verra plus tard comment régler ça.
bot.cogs_loaded = False


@bot.event
async def on_ready():
    """Log in Discord."""
    logging.info('Logged in as')
    logging.info(bot.user.name)
    logging.info(bot.user.id)

    if not bot.cogs_loaded:
        bot.guild = bot.get_guild(GUILD_ID)
        bot.nsfw_channel = discord.utils.get(bot.guild.text_channels, name=NSFW_BOT_CHANNEL)
        bot.nsfw_channel_manual = discord.utils.get(bot.guild.text_channels, name=NSFW_MANUAL_CHANNEL)

        for ext in cogs_ext_list:
            await bot.load_extension(ext)

        await bot.tree.sync()
        bot.cogs_loaded = True
        logging.info("Cogs loaded and channels set.")


# I put the load_extensions back in on_ready, because the problem
# was that load_extensions was triggered before connection, so nsfw_channel wasn't initialised
# TODO later.
# @bot.event
# async def setup_hook():
#     """A coroutine to be called to setup the bot.

#     To perform asynchronous setup after the bot is logged in but before
#     it has connected to the Websocket, overwrite this coroutine.

#     This is only called once, in `login`, and will be called before
#     any events are dispatched, making it a better solution than doing such
#     setup in the `~discord.on_ready` event.

#     Warning :
#     Since this is called *before* the websocket connection is made therefore
#     anything that waits for the websocket will deadlock, this includes things
#     like :meth:`wait_for` and :meth:`wait_until_ready`.
#     """
#     logging.info("Setup_hook !!!")
#     for ext in cogs_ext_list:
#         await bot.load_extension(ext)


if __name__ == "__main__":
    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    logging.info("New bot with discord.py version %s", discord.__version__)
    bot.run(TOKEN)
