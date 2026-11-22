from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message


_last_bot_messages: dict[int, int] = {}


async def send_replacing_message(
    bot: Bot,
    chat_id: int,
    text: str,
    **kwargs,
) -> Message:
    """Send a bot message after removing the previous tracked bot message."""
    previous_message_id = _last_bot_messages.get(chat_id)
    if previous_message_id:
        try:
            await bot.delete_message(chat_id, previous_message_id)
        except TelegramAPIError:
            pass

    message = await bot.send_message(chat_id, text, **kwargs)
    _last_bot_messages[chat_id] = message.message_id
    return message


def remember_bot_message(message: Message) -> None:
    _last_bot_messages[message.chat.id] = message.message_id
