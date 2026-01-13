from unittest.mock import MagicMock

import discord
import pytest

from utils.tools import get_last_bot_messages


class FakeAsyncHistory:
    def __init__(self, messages):
        self._messages = messages

    def __aiter__(self):
        async def generator():
            for msg in self._messages:
                yield msg
        return generator()


@pytest.mark.asyncio
async def test_get_last_bot_messages_filters_by_bot_user():
    bot_user = MagicMock(spec=discord.ClientUser)
    bot_user.id = 123

    message_from_bot = MagicMock(spec=discord.Message)
    message_from_bot.author = bot_user
    message_from_bot.content = "image_url_1"

    message_from_other = MagicMock(spec=discord.Message)
    message_from_other.author = MagicMock()
    message_from_other.author.id = 999
    message_from_other.content = "image_url_2"

    channel = MagicMock(spec=discord.TextChannel)
    channel.history.return_value = FakeAsyncHistory([message_from_bot, message_from_other])

    result = await get_last_bot_messages(channel, bot_user, max_tries=1, history_limit=10)

    assert result == ["image_url_1"]
